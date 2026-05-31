import httpx
import json
import base64
from config import GITHUB_TOKEN, GITHUB_QUEUE_REPO

_BASE = "https://api.github.com"
_HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


async def enqueue(process_id: str, intent: str, project: str, job: dict) -> None:
    path = f"queue/{process_id}.json"
    payload = json.dumps({"process_id": process_id, "intent": intent, "project": project, "job": job})
    encoded = base64.b64encode(payload.encode()).decode()
    async with httpx.AsyncClient() as client:
        r = await client.put(
            f"{_BASE}/repos/{GITHUB_QUEUE_REPO}/contents/{path}",
            headers=_HEADERS,
            json={"message": f"queue: {job['analysis']['title']}", "content": encoded},
        )
        r.raise_for_status()


async def get_pending() -> list[dict]:
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{_BASE}/repos/{GITHUB_QUEUE_REPO}/contents/queue",
            headers=_HEADERS,
        )
        if r.status_code == 404:
            return []
        r.raise_for_status()
        items = []
        for f in r.json():
            if not f["name"].endswith(".json"):
                continue
            dr = await client.get(f["download_url"])
            data = dr.json()
            data["_sha"] = f["sha"]
            data["_path"] = f["path"]
            items.append(data)
        return items


async def dequeue(path: str, sha: str, title: str) -> None:
    async with httpx.AsyncClient() as client:
        r = await client.delete(
            f"{_BASE}/repos/{GITHUB_QUEUE_REPO}/contents/{path}",
            headers=_HEADERS,
            json={"message": f"processed: {title}", "sha": sha},
        )
        r.raise_for_status()
