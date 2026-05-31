"""
flush.py — run on the PC (via Task Scheduler) to sync queued reels into Obsidian.
Hits the Render server for pending items, writes them locally, then acknowledges.
"""
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv()

from config import RENDER_URL
from router import route_to_obsidian


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
                await client.post(
                    f"{RENDER_URL}/acknowledge",
                    json={"path": item["_path"], "sha": item["_sha"], "title": title},
                )
                print(f"  OK: {title}")
            except Exception as e:
                print(f"  FAIL: {title}: {e}")


if __name__ == "__main__":
    asyncio.run(flush())
