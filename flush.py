"""
flush.py — run on the PC (via Task Scheduler) to sync queued reels into Obsidian.
Pulls pending items from Railway, writes to Obsidian locally, deletes from GitHub directly.
"""
import asyncio
import json
import httpx
from dotenv import load_dotenv

load_dotenv()

from config import RENDER_URL, GITHUB_TOKEN, GITHUB_QUEUE_REPO
from router import route_to_obsidian

_GH_HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


async def flush():
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{RENDER_URL}/pending")
        r.raise_for_status()
        data = r.json()

    pending = data.get("items", [])
    if not pending:
        print("Nothing to flush.")
        return

    print(f"{len(pending)} item(s) queued.")

    async with httpx.AsyncClient(timeout=30) as client:
        for item in pending:
            title = item["job"]["analysis"]["title"]
            try:
                await route_to_obsidian(item["job"], item["intent"], item.get("project", ""))
                # Delete directly from GitHub — bypasses Railway /acknowledge
                r = await client.request(
                    "DELETE",
                    f"https://api.github.com/repos/{GITHUB_QUEUE_REPO}/contents/{item['_path']}",
                    headers={**_GH_HEADERS, "Content-Type": "application/json"},
                    content=json.dumps({"message": f"processed: {title}", "sha": item["_sha"]}).encode(),
                )
                r.raise_for_status()
                print(f"  OK: {title}")
            except Exception as e:
                print(f"  FAIL: {title}: {e}")


if __name__ == "__main__":
    asyncio.run(flush())
