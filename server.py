"""
Reel Pipeline Server
--------------------
Two endpoints:

POST /process  — takes a reel URL, downloads + transcribes + analyzes it.
                 Returns a summary + suggested intent for the user to confirm.

POST /route    — takes the process_id from /process plus the user's chosen intent,
                 then writes the appropriate notes to Obsidian.

Run with:  python server.py
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from pipeline import process_reel_url
from router import route_to_obsidian
import queue_manager
from config import SERVER_PORT, GITHUB_QUEUE_REPO

app = FastAPI(title="Reel Pipeline", version="1.0.0")

# Simple in-memory job store — jobs live until routed or server restarts.
# For v1 this is fine; upgrade to Redis if you want persistence.
_jobs: dict[str, dict] = {}


# ---------- Request / Response models ----------

class ProcessRequest(BaseModel):
    url: str
    note: str = ""


class ProcessResponse(BaseModel):
    process_id: str
    title: str
    summary: str
    key_points: list[str]
    tags: list[str]
    suggested_intent: str   # catalog | try_this | implement | inbox
    intent_reason: str


class RouteRequest(BaseModel):
    process_id: str
    intent: str             # catalog | try_this | implement | inbox
    project: str = ""       # only needed when intent == "implement"
    extra: str = ""


class RouteResponse(BaseModel):
    status: str
    message: str
    paths: list[str]


class AcknowledgeRequest(BaseModel):
    path: str
    sha: str
    title: str


# ---------- Endpoints ----------

@app.post("/process", response_model=ProcessResponse)
async def process_reel(req: ProcessRequest):
    """
    Step 1 — Download, transcribe, and analyze a reel.
    Call this when the user shares a URL. Returns a summary + intent suggestion
    for the user to review before anything is written to Obsidian.
    """
    try:
        job = await process_reel_url(req.url, req.note)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {e}")

    _jobs[job["id"]] = job
    analysis = job["analysis"]

    return ProcessResponse(
        process_id=job["id"],
        title=analysis["title"],
        summary=analysis["summary"],
        key_points=analysis.get("key_points", []),
        tags=analysis.get("tags", []),
        suggested_intent=analysis["suggested_intent"],
        intent_reason=analysis["intent_reason"],
    )


@app.post("/route", response_model=RouteResponse)
async def route_reel(req: RouteRequest):
    """
    Step 2 — Route the processed reel to Obsidian based on the user's chosen intent.
    Must be called after /process with the returned process_id.
    """
    job = _jobs.get(req.process_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found. It may have expired (server restarted) or already been routed.",
        )

    if GITHUB_QUEUE_REPO:
        # Cloud mode: always queue to GitHub, PC flushes to Obsidian
        try:
            await queue_manager.enqueue(req.process_id, req.intent, req.project, job)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Queue failed: {e}")
        del _jobs[req.process_id]
        return RouteResponse(
            status="queued",
            message=f"Saved — syncs to Obsidian shortly: \"{job['analysis']['title']}\"",
            paths=[],
        )

    # Local mode: write directly to Obsidian
    try:
        result = await route_to_obsidian(job, req.intent, req.project, req.extra)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Routing failed: {e}")

    del _jobs[req.process_id]
    return RouteResponse(**result)


@app.get("/pending")
async def get_pending():
    """Return all queued items waiting to be written to Obsidian."""
    items = await queue_manager.get_pending()
    return {"count": len(items), "items": items}


@app.post("/acknowledge")
async def acknowledge(req: AcknowledgeRequest):
    """Called by the PC flush script after successfully writing an item to Obsidian."""
    try:
        await queue_manager.dequeue(req.path, req.sha, req.title)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Acknowledge failed: {e}")
    return {"status": "ok", "title": req.title}


@app.get("/health")
def health():
    return {"status": "ok", "pending_jobs": len(_jobs)}


# ---------- Run ----------

if __name__ == "__main__":
    import uvicorn
    print(f"Starting Reel Pipeline on port {SERVER_PORT}")
    uvicorn.run("server:app", host="0.0.0.0", port=SERVER_PORT, reload=False)
