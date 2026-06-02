import yt_dlp
import tempfile
import os
import uuid
import json
from datetime import datetime
from openai import AsyncOpenAI
import anthropic

from config import GROQ_API_KEY, ANTHROPIC_API_KEY

openai_client = AsyncOpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


async def download_reel(url: str, output_dir: str) -> tuple[str, dict]:
    """
    Download Instagram reel audio using yt-dlp.
    Returns (audio_file_path, metadata_dict).
    Requires ffmpeg installed and on PATH.
    """
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(output_dir, "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        video_id = info.get("id", "reel")
        metadata = {
            "title": info.get("title", ""),
            "description": info.get("description", ""),
            "uploader": info.get("uploader", "Unknown"),
            "uploader_id": info.get("uploader_id", ""),
            "duration": info.get("duration", 0),
            "url": url,
        }

    # Find the downloaded audio file (m4a, webm, etc — Groq Whisper accepts all)
    audio_path = None
    for f in os.listdir(output_dir):
        if f.startswith(video_id):
            audio_path = os.path.join(output_dir, f)
            break
    if not audio_path:
        # Fallback: grab whatever was downloaded
        files = os.listdir(output_dir)
        if files:
            audio_path = os.path.join(output_dir, files[0])

    return audio_path, metadata


async def transcribe_audio(audio_path: str) -> str:
    """
    Transcribe audio using OpenAI Whisper API.
    Falls back to empty string if audio has no speech.
    """
    with open(audio_path, "rb") as f:
        response = await openai_client.audio.transcriptions.create(
            model="whisper-large-v3",
            file=f,
            response_format="text",
        )
    return response or ""


async def analyze_with_claude(transcript: str, metadata: dict, user_note: str) -> dict:
    """
    Use Claude Haiku to generate title, summary, key points, tags, and suggested intent.
    Returns a structured dict.
    """
    description_snippet = (metadata.get("description") or "")[:500]
    transcript_snippet = transcript[:3000] if transcript else "(no speech detected — music or visual-only reel)"

    prompt = f"""You are processing an Instagram Reel that a user shared to save into their personal knowledge base.

Reel info:
- Posted by: @{metadata.get("uploader", "unknown")}
- Caption: {description_snippet or "(none)"}
- User's note: {user_note or "(none)"}

Transcript:
{transcript_snippet}

Respond with a JSON object containing exactly these fields:
{{
  "title": "Clear descriptive title, 5-10 words",
  "summary": "2-3 sentences explaining what this reel is about",
  "key_points": ["point 1", "point 2", "point 3"],
  "tags": ["tag1", "tag2", "tag3"],
  "suggested_intent": "one of: catalog | try_this | implement | inbox",
  "intent_reason": "One sentence explaining your suggestion"
}}

Intent guide:
- catalog: general knowledge worth keeping (tutorial, tip, fact, explanation)
- try_this: something to do or try (recipe, workout, place, activity, product)
- implement: actionable for a personal project or workflow
- inbox: unclear — save it and let the user decide later

Return only the JSON object, no markdown.
"""

    message = anthropic_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


async def process_reel_url(url: str, user_note: str = "") -> dict:
    """
    Full pipeline: URL → download → transcribe → analyze → result dict.
    This is called by the /process endpoint and returns everything
    needed for the user to pick an intent.
    """
    job_id = str(uuid.uuid4())[:8]

    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path, metadata = await download_reel(url, tmpdir)
        transcript = await transcribe_audio(audio_path)

    analysis = await analyze_with_claude(transcript, metadata, user_note)

    return {
        "id": job_id,
        "url": url,
        "metadata": metadata,
        "transcript": transcript,
        "analysis": analysis,
        "timestamp": datetime.now().isoformat(),
        "user_note": user_note,
    }
