import asyncio
import json
import re
import ssl
import time
from pathlib import Path
from typing import Any, Dict, List, Literal

import aiohttp
import certifi
import structlog

from src.config import GITHUB_TOKEN

logger = structlog.get_logger(__name__)


class GitHubAPI:
    def __init__(self, token: str = GITHUB_TOKEN):
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitHub-Followers-Analyzer",
        }
        if token:
            self.headers["Authorization"] = f"token {token}"
        else:
            logger.warning(
                "No GitHub token found, rate limits will be restricted (60/hour)"
            )

    async def _fetch_page(
        self, session: aiohttp.ClientSession, url: str
    ) -> tuple[List[Dict[str, Any]], int]:
        """Fetch a single page and return items + last page number."""
        while True:
            start_time = time.monotonic()
            async with session.get(url, headers=self.headers) as response:
                duration = time.monotonic() - start_time

                remaining = response.headers.get("X-RateLimit-Remaining")
                reset_time = response.headers.get("X-RateLimit-Reset")

                logger.info(
                    "api_request",
                    url=url,
                    status=response.status,
                    duration=duration,
                    remaining=remaining,
                )

                if response.status == 403 and remaining == "0":
                    reset_ts = int(reset_time) if reset_time else time.time() + 60
                    sleep_time = max(0, reset_ts - time.time()) + 1
                    
                    if sleep_time > 60:
                        logger.error("rate_limit_exceeded_long", sleep_for=sleep_time)
                        raise Exception(
                            f"GitHub API 限流！请在左侧侧边栏输入 GitHub Token 以解除 60次/小时 的限制。(需要等待 {int(sleep_time/60)} 分钟)"
                        )
                        
                    logger.warning("rate_limit_exceeded", sleep_for=sleep_time)
                    await asyncio.sleep(sleep_time)
                    continue

                response.raise_for_status()
                data = await response.json()

                # Check for pagination last link
                last_page = 1
                if "Link" in response.headers:
                    links = response.headers["Link"].split(", ")
                    for link in links:
                        if 'rel="last"' in link:
                            last_url = link[link.find("<") + 1 : link.find(">")]
                            match = re.search(r"[?&]page=(\d+)", last_url)
                            if match:
                                last_page = int(match.group(1))
                            break

                return data, last_page

    async def fetch_users(
        self, username: str, relation_type: Literal["followers", "following"]
    ) -> List[Dict[str, Any]]:
        """Fetch all followers or following for a user concurrently."""
        base_url = f"https://api.github.com/users/{username}/{relation_type}?per_page=100"
        all_users = []

        # Fix SSL certificate verification issue on macOS
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        connector = aiohttp.TCPConnector(ssl=ssl_context, limit=10) # Limit concurrent connections

        async with aiohttp.ClientSession(connector=connector) as session:
            # Fetch first page to determine total pages
            first_page_url = f"{base_url}&page=1"
            users, last_page = await self._fetch_page(session, first_page_url)
            all_users.extend(users)

            if last_page > 1:
                logger.info(f"Concurrent fetching {last_page - 1} pages for {relation_type}...")
                tasks = []
                for page in range(2, last_page + 1):
                    page_url = f"{base_url}&page={page}"
                    tasks.append(self._fetch_page(session, page_url))
                
                results = await asyncio.gather(*tasks)
                for res, _ in results:
                    all_users.extend(res)

        # Save raw JSON
        timestamp = int(time.time())
        raw_dir = Path("data/raw")
        raw_dir.mkdir(parents=True, exist_ok=True)
        file_path = raw_dir / f"{username}_{relation_type}_{timestamp}.json"

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(all_users, f, ensure_ascii=False, indent=2)

        logger.info("raw_data_saved", file=str(file_path), count=len(all_users))
        return all_users

    async def fetch_all(
        self, username: str
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Fetch both followers and following concurrently."""
        followers_task = self.fetch_users(username, "followers")
        following_task = self.fetch_users(username, "following")

        return await asyncio.gather(followers_task, following_task)
