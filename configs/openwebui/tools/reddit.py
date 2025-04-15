"""
title: Reddit
author: @nathanwindisch
author_url: https://git.wnd.sh/owui-tools/reddit
funding_url: https://patreon.com/NathanWindisch
version: 0.0.1
changelog:
- 0.0.1 - Initial upload to openwebui community.
- 0.0.2 - Renamed from "Reddit Feeds" to just "Reddit".
- 0.0.3 - Updated author_url in docstring to point to 
          git repo.
"""


import re
import json
import requests
from typing import Awaitable, Callable
from pydantic import BaseModel, Field
from requests.models import Response


def parse_reddit_page(response: Response):
	data = json.loads(response.content)
	output = []
	if "data" not in data: return output
	if "children" not in data["data"]: return output
	for item in data["data"]["children"]: output.append(item)
	return output


def parse_posts(data: list):
	posts = []
	for item in data:
		if item["kind"] != "t3": continue
		item = item["data"]
		posts.append({
			"id": item["name"],
			"title": item["title"],
			"description": item["selftext"],
			"link": item["url"],

			"author_username": item["author"],
			"author_id": item["author_fullname"],
			"subreddit_name": item["subreddit"],
			"subreddit_id": item["subreddit_id"],
			"subreddit_subscribers": item["subreddit_subscribers"],

			"score": item["score"],
			"upvotes": item["ups"],
			"downvotes": item["downs"],
			"upvote_ratio": item["upvote_ratio"],
			"total_comments": item["num_comments"],
			"total_crossposts": item["num_crossposts"],
			"total_awards": item["total_awards_received"],
			"domain": item["domain"],
			"flair_text": item["link_flair_text"],
			"media_embed": item["media_embed"],

			"is_pinned": item["pinned"],
			"is_self": item["is_self"],
			"is_video": item["is_video"],
			"is_media_only": item["media_only"],
			"is_over_18": item["over_18"],
			"is_edited": item["edited"],
			"is_hidden": item["hidden"],
			"is_archived": item["archived"],
			"is_locked": item["locked"],
			"is_quarantined": item["quarantine"],
			"is_spoiler": item["spoiler"],
			"is_stickied": item["stickied"],
			"is_send_replies": item["send_replies"],

			"published_at": item["created_utc"],
		})
	return posts


def parse_comments(data: list):
	comments = []
	for item in data:
		if item["kind"] != "t1": continue
		item = item["data"]
		comments.append({
			"id": item["name"],
			"body": item["body"],
			"link": item["permalink"],
			"post_id": item["link_id"],
			"post_title": item["link_title"],
			"post_link": item["link_permalink"],

			"author_username": item["author"],
			"author_id": item["author_fullname"],
			"subreddit_name": item["subreddit"],
			"subreddit_id": item["subreddit_id"],

			"score": item["score"],
			"upvotes": item["ups"],
			"downvotes": item["downs"],
			"total_comments": item["num_comments"],
			"total_awards": item["total_awards_received"],
			"is_edited": item["edited"],
			"is_archived": item["archived"],
			"is_locked": item["locked"],
			"is_quarantined": item["quarantine"],
			"is_stickied": item["stickied"],
			"is_send_replies": item["send_replies"],
			"published_at": item["created_utc"],
		})
	return comments


class Tools:
	def __init__(self): pass

	class UserValves(BaseModel):
		USER_AGENT: str = Field(
			default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
			description="The user agent to use when making requests to Reddit."
		)

	async def get_subreddit_feed(
		self,
		subreddit: str,
		__event_emitter__: Callable[[dict], Awaitable[None]],
		__user__: dict = {},
	) -> str:
		"""
		Get the latest posts from a subreddit, as an array of JSON objects with the following properties: 'id', 'title', 'description', 'link', 'author_username', 'author_id', 'subreddit_name', 'subreddit_id', 'subreddit_subscribers', 'score', 'upvotes', 'downvotes', 'upvote_ratio', 'total_comments', 'total_crossposts', 'total_awards', 'domain', 'flair_text', 'media_embed', 'is_pinned', 'is_self', 'is_video', 'is_media_only', 'is_over_18', 'is_edited', 'is_hidden', 'is_archived', 'is_locked', 'is_quarantined', 'is_spoiler', 'is_stickied', 'is_send_replies', 'published_at'.
		:param subreddit: The subreddit to get the latest posts from.
		:return: A list of posts with the previously mentioned properties, or an error message.
		"""
		headers = { "User-Agent": __user__["valves"].USER_AGENT }
		await __event_emitter__({ "data": { "description": f"Starting retrieval for r/{subreddit}'s Reddit Feed...", "status": "in_progress", "done": False }, "type": "status" })

		if subreddit == "":
			await __event_emitter__({ "data": { "description": f"Error: No subreddit provided.", "status": "complete", "done": True }, "type": "status" })
			return "Error: No subreddit provided"
		subreddit = subreddit.replace("/r/", "").replace("r/", "")

		if not re.match(r"^[A-Za-z0-9_]{2,21}$", subreddit):
			await __event_emitter__({ "data": { "description": f"Error: Invalid subreddit name '{subreddit}' (either too long or two short).", "status": "complete", "done": True }, "type": "status" })
			return "Error: Invalid subreddit name"

		try:
			response = requests.get(f"https://reddit.com/r/{subreddit}.json", headers=headers)

			if not response.ok:
				await __event_emitter__({ "data": { "description": f"Error: Failed to retrieve r/{subreddit}'s Reddit Feed: {response.status_code}.", "status": "complete", "done": True }, "type": "status" })
				return f"Error: {response.status_code}"
			else:
				output = parse_posts(parse_reddit_page(response))
				await __event_emitter__({ "data": { "description": f"Retrieved {len(output)} posts from r/{subreddit}'s Reddit Feed.", "status": "complete", "done": True }, "type": "status" })
				return json.dumps(output)
		except Exception as e:
			await __event_emitter__({ "data": { "description": f"Failed to retrieve any posts from r/{subreddit}'s Reddit Feed: {e}.", "status": "complete", "done": True }, "type": "status" })
			return f"Error: {e}"


	async def get_user_feed(
		self,
		username: str,
		__event_emitter__: Callable[[dict], Awaitable[None]],
		__user__: dict = {},
	) -> str:
		"""
		Get the latest posts from a given user, as a JSON object with an array of 'post' objects with the following properties: 'id', 'title', 'description', 'link', 'author_username', 'author_id', 'subreddit_name', 'subreddit_id', 'subreddit_subscribers', 'score', 'upvotes', 'downvotes', 'upvote_ratio', 'total_comments', 'total_crossposts', 'total_awards', 'domain', 'flair_text', 'media_embed', 'is_pinned', 'is_self', 'is_video', 'is_media_only', 'is_over_18', 'is_edited', 'is_hidden', 'is_archived', 'is_locked', 'is_quarantined', 'is_spoiler', 'is_stickied', 'is_send_replies', 'published_at'.
		Additionally, the resultant object will also contain an array of 'comment' objects with the following properties: 'id', 'body', 'link', 'post_id', 'post_title', 'post_link', 'author_id', 'post_author_username', 'subreddit_name', 'subreddit_id', 'subreddit_subscribers', 'score', 'upvotes', 'downvotes', 'total_comments', 'total_awards', 'is_edited', 'is_archived', 'is_locked', 'is_quarantined', 'is_stickied', 'is_send_replies', 'published_at'.
		:param username: The username to get the latest posts from.
		:return: A object with list of posts and a list of comments (both with the previously mentioned properties), or an error message.
		"""
		headers = { "User-Agent": __user__["valves"].USER_AGENT }
		await __event_emitter__({ "data": { "description": f"Starting retrieval for u/{username}'s Reddit Feed...", "status": "in_progress", "done": False }, "type": "status" })

		if username == "":
			await __event_emitter__({ "data": { "description": f"Error: No username provided.", "status": "complete", "done": True }, "type": "status" })
			return "Error: No username provided."
		username = username.replace("/u/", "").replace("u/", "")

		if not re.match(r"^[A-Za-z0-9_]{3,20}$", username):
			await __event_emitter__({ "data": { "description": f"Error: Invalid username '{username}' (either too long or two short).", "status": "complete", "done": True }, "type": "status" })
			return "Error: Invalid username."

		try:
			response = requests.get(f"https://reddit.com/u/{username}.json", headers=headers)

			if not response.ok:
				await __event_emitter__({ "data": { "description": f"Error: Failed to retrieve u/{username}'s Reddit Feed: {response.status_code}.", "status": "complete", "done": True }, "type": "status" })
				return f"Error: {response.status_code}"
			else:
				page = parse_reddit_page(response) # user pages can have both posts and comments.
				posts = parse_posts(page)
				comments = parse_comments(page)
				await __event_emitter__({ "data": { "description": f"Retrieved {len(posts)} posts and {len(comments)} comments from u/{username}'s Reddit Feed.", "status": "complete", "done": True }, "type": "status" })
				return json.dumps({ "posts": posts, "comments": comments })
		except Exception as e:
			await __event_emitter__({ "data": { "description": f"Failed to retrieve any posts from u/{username}'s Reddit Feed: {e}.", "status": "complete", "done": True }, "type": "status" })
			return f"Error: {e}"
