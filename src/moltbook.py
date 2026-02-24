"""Moltbook API client — scout projects and post agent reports."""

import json
import time
import logging
import hashlib
from datetime import datetime, timezone
from typing import Optional

import httpx

from . import config

log = logging.getLogger("surgescout.moltbook")

# ---------------------------------------------------------------------------
# Moltbook client
# ---------------------------------------------------------------------------

class MoltbookClient:
    """Read from and write to Moltbook submolts."""

    def __init__(self, base_url: str = "", submolt: str = ""):
        self.base_url = (base_url or config.MOLTBOOK_API_URL).rstrip("/")
        self.submolt = submolt or config.MOLTBOOK_SUBMOLT
        self._http = httpx.Client(timeout=30, follow_redirects=True)

    # ------ read ------

    def fetch_posts(self, submolt: str = "", limit: int = 50, sort: str = "new") -> list[dict]:
        """Fetch recent posts from a submolt."""
        sub = submolt or self.submolt
        url = f"{self.base_url}/api/v1/submolts/{sub}/posts"
        try:
            r = self._http.get(url, params={"limit": limit, "sort": sort})
            r.raise_for_status()
            data = r.json()
            return data if isinstance(data, list) else data.get("posts", data.get("data", []))
        except Exception as e:
            log.warning(f"Moltbook fetch failed ({sub}): {e}")
            return []

    def fetch_trending(self, limit: int = 30) -> list[dict]:
        """Fetch trending posts across Moltbook."""
        url = f"{self.base_url}/api/v1/posts/trending"
        try:
            r = self._http.get(url, params={"limit": limit})
            r.raise_for_status()
            data = r.json()
            return data if isinstance(data, list) else data.get("posts", data.get("data", []))
        except Exception as e:
            log.warning(f"Moltbook trending fetch failed: {e}")
            return []

    def search_posts(self, query: str, limit: int = 30) -> list[dict]:
        """Search Moltbook posts by keyword."""
        url = f"{self.base_url}/api/v1/search"
        try:
            r = self._http.get(url, params={"q": query, "limit": limit, "type": "posts"})
            r.raise_for_status()
            data = r.json()
            return data if isinstance(data, list) else data.get("results", data.get("data", []))
        except Exception as e:
            log.warning(f"Moltbook search failed: {e}")
            return []

    # ------ write ------

    def post_update(self, title: str, body: str, submolt: str = "") -> dict:
        """Post an update to a submolt (requires agent auth via OpenClaw)."""
        sub = submolt or self.submolt
        url = f"{self.base_url}/api/v1/submolts/{sub}/posts"
        payload = {
            "title": title,
            "body": body,
            "type": "text",
        }
        try:
            r = self._http.post(url, json=payload)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            log.warning(f"Moltbook post failed: {e}")
            return {"error": str(e)}

    def post_comment(self, post_id: str, body: str) -> dict:
        """Comment on an existing post."""
        url = f"{self.base_url}/api/v1/posts/{post_id}/comments"
        try:
            r = self._http.post(url, json={"body": body})
            r.raise_for_status()
            return r.json()
        except Exception as e:
            log.warning(f"Moltbook comment failed: {e}")
            return {"error": str(e)}


# ---------------------------------------------------------------------------
# Project extraction helpers
# ---------------------------------------------------------------------------

def extract_projects_from_posts(posts: list[dict]) -> list[dict]:
    """Parse Moltbook posts to extract potential project references.

    Looks for: GitHub links, token mentions, project descriptions,
    hackathon submissions, launch announcements.
    """
    import re

    projects = []
    seen = set()

    for post in posts:
        body = post.get("body", "") or post.get("content", "") or ""
        title = post.get("title", "") or ""
        author = post.get("author", {})
        if isinstance(author, dict):
            author_name = author.get("username", author.get("name", "unknown"))
        else:
            author_name = str(author)

        # Extract GitHub URLs
        gh_urls = re.findall(r'https?://github\.com/[\w\-]+/[\w\-]+', body)

        # Extract token mentions ($TOKEN)
        tokens = re.findall(r'\$([A-Z]{2,10})', body)

        # Look for project-like content
        has_project_signals = any([
            gh_urls,
            tokens,
            any(kw in body.lower() for kw in [
                "launch", "deploy", "built", "ship", "release",
                "token", "contract", "dapp", "agent", "skill",
                "hackathon", "submission", "demo",
            ]),
        ])

        if not has_project_signals:
            continue

        # Deduplicate by content hash
        content_hash = hashlib.md5(f"{title}{body[:200]}".encode()).hexdigest()[:12]
        if content_hash in seen:
            continue
        seen.add(content_hash)

        projects.append({
            "id": post.get("id", content_hash),
            "title": title,
            "body": body[:2000],
            "author": author_name,
            "github_urls": gh_urls,
            "token_mentions": tokens,
            "votes": post.get("votes", post.get("upvotes", 0)),
            "comments": post.get("comment_count", post.get("comments", 0)),
            "created_at": post.get("created_at", post.get("createdAt", "")),
            "url": post.get("url", post.get("permalink", "")),
            "submolt": post.get("submolt", {}).get("name", "") if isinstance(post.get("submolt"), dict) else "",
            "source": "moltbook",
        })

    return projects


def scout_moltbook(submolts: list[str] | None = None, keywords: list[str] | None = None) -> list[dict]:
    """Full scouting pipeline: fetch from multiple sources and extract projects."""
    client = MoltbookClient()
    all_posts = []

    # 1. Fetch from target submolts
    target_submolts = submolts or ["lablab", "cryptocurrency", "defi", "agents", "startups"]
    for sub in target_submolts:
        posts = client.fetch_posts(sub, limit=50, sort="new")
        all_posts.extend(posts)
        log.info(f"Fetched {len(posts)} posts from m/{sub}")

    # 2. Fetch trending
    trending = client.fetch_trending(limit=30)
    all_posts.extend(trending)
    log.info(f"Fetched {len(trending)} trending posts")

    # 3. Search by keywords
    search_keywords = keywords or ["token launch", "new project", "hackathon", "deploy", "agent skill"]
    for kw in search_keywords:
        results = client.search_posts(kw, limit=20)
        all_posts.extend(results)

    # 4. Extract projects
    projects = extract_projects_from_posts(all_posts)
    log.info(f"Extracted {len(projects)} project candidates from {len(all_posts)} posts")

    return projects
