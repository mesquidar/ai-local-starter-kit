"""
title: Flowise Integration for OpenWebUI
author: LTech Consultancy
version: 0.6
description: A seamless integration between OpenWebUI and Flowise AI, enabling natural conversations with full chat history support. Features include:
  - Maintains complete chat history for contextual conversations
  - Secure API key authentication
  - System message support for conversation control
  - Enhanced error handling and message processing
  - Improved streaming support
Requirements:
  - Flowise API URL (set via FLOWISE_API_URL)
  - Flowise API Key (set via FLOWISE_API_KEY)
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Union, Generator, Iterator
import requests
import json
import os
from open_webui.utils.misc import pop_system_message


class Pipe:
    class Valves(BaseModel):
        flowise_prediction_url: str = Field(
            default=os.getenv("FLOWISE_API_URL", ""),
            description="Full Flowise prediction endpoint URL",
        )
        flowise_api_key: str = Field(
            default=os.getenv("FLOWISE_API_KEY", ""),
            description="Flowise API key for authentication",
        )
        max_history: int = Field(
            default=10,
            description="Maximum number of messages to include in chat history",
        )

    def __init__(self):
        self.type = "manifold"
        self.id = "flowise_chat"
        self.name = "Flowise AI Chatflow"
        self.valves = self.Valves()

        # Validate required settings
        if not self.valves.flowise_prediction_url:
            print(
                "⚠️ Please set your Flowise URL using the FLOWISE_API_URL environment variable"
            )
        if not self.valves.flowise_api_key:
            print(
                "⚠️ Please set your Flowise API key using the FLOWISE_API_KEY environment variable"
            )

    def pipes(self) -> List[dict]:
        return [{"id": "flowise_chat", "name": "Flowise AI Chat"}]

    def _process_message_content(self, message: dict) -> str:
        """Process message content, handling both text and multi-modal content"""
        if isinstance(message.get("content"), list):
            # Handle multi-modal content (if Flowise supports it)
            processed_content = []
            for item in message["content"]:
                if item["type"] == "text":
                    processed_content.append(item["text"])
            return " ".join(processed_content)
        return message.get("content", "")

    def _process_message(self, message: dict) -> dict:
        """Process a single message for Flowise API"""
        content = self._process_message_content(message)
        # Map OpenWebUI roles to Flowise roles (userMessage/apiMessage)
        role_mapping = {"user": "userMessage", "assistant": "apiMessage"}
        return {
            "role": role_mapping.get(message.get("role", "user"), "userMessage"),
            "content": content,
        }

    def pipe(self, body: dict, __user__: Optional[dict] = None) -> Union[str, Generator, Iterator]:
        """Process chat messages through Flowise"""
        try:
            print("\nProcessing Flowise request:")
            print(f"Request body: {json.dumps(body, indent=2)}")
            
            # Extract messages from the body
            messages = body.get("messages", [])
            if not messages:
                raise Exception("No messages found in request body")

            # Get the current message (last message)
            current_message = messages[-1]
            question = self._process_message_content(current_message)

            # Process previous messages as history
            history = []
            if len(messages) > 1:  # If we have previous messages
                for msg in messages[:-1]:  # Exclude current message
                    history.append(self._process_message(msg))

            # Prepare request payload according to Flowise API format
            data = {
                "question": question,      # Current message
                "history": history,        # Previous messages in Flowise format
                "overrideConfig": {},      # Optional configuration
            }

            # Handle system message if present
            for msg in messages:
                if msg.get("role") == "system":
                    data["systemMessage"] = msg.get("content", "")
                    break

            headers = {
                "Authorization": f"Bearer {self.valves.flowise_api_key}",
                "Content-Type": "application/json",
            }

            print("\nMaking Flowise API request:")
            print(f"URL: {self.valves.flowise_prediction_url}")
            print(f"Headers: {headers}")
            print(f"Data: {json.dumps(data, indent=2)}")

            # Make the API request
            r = requests.post(
                url=self.valves.flowise_prediction_url,
                json=data,
                headers=headers,
                stream=body.get("stream", False)
            )
            r.raise_for_status()

            # Return response based on streaming preference
            if body.get("stream", False):
                for line in r.iter_lines():
                    if line:
                        try:
                            # Parse the JSON response
                            response = json.loads(line.decode())
                            # Only return the text field from the response
                            if isinstance(response, dict) and "text" in response:
                                yield response["text"]
                        except json.JSONDecodeError:
                            # If it's not JSON, yield the line as is
                            yield line.decode()
            else:
                response = r.json()
                # Only return the text field from the response
                if isinstance(response, dict) and "text" in response:
                    return response["text"]
                return ""

        except Exception as e:
            error_msg = f"Error in Flowise pipe: {str(e)}"
            print(error_msg)
            return error_msg
