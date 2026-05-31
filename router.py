from datetime import datetime
from obsidian_client import write_note, append_to_note
from config import VAULT_RAW_FOLDER, VAULT_WIKI_FOLDER, VAULT_INBOX_FOLDER, VAULT_TRY_THIS_NOTE


def _safe_filename(title: str, max_len: int = 50) -> str:
    """Sanitize a title for use as a filename."""
    replacements = [("/", "-"), (":", "-"), ("\\", "-"), ('"', ""), ("?", ""), ("*", ""), ("|", "-")]
    result = title
    for old, new in replacements:
        result = result.replace(old, new)
    return result[:max_len].strip()


def _build_raw_note(job: dict) -> str:
    analysis = job["analysis"]
    meta = job["metadata"]
    date = job["timestamp"][:10]
    tags_inline = " ".join(f"#{t}" for t in analysis.get("tags", []))
    key_points = "\n".join(f"- {p}" for p in analysis.get("key_points", []))
    transcript = job.get("transcript", "").strip() or "_No speech detected._"
    user_note = job.get("user_note", "").strip() or "_None_"

    return f"""---
source: instagram-reel
url: {job["url"]}
uploader: "@{meta.get("uploader", "unknown")}"
date: {date}
---

# {analysis["title"]}

{tags_inline}

## Summary
{analysis["summary"]}

## Key Points
{key_points}

## Transcript
{transcript}

## User Note
{user_note}
"""


def _build_wiki_note(job: dict, raw_path: str) -> str:
    analysis = job["analysis"]
    date = job["timestamp"][:10]
    tags_yaml = "\n".join(f"  - {t}" for t in analysis.get("tags", []))
    key_points = "\n".join(f"- {p}" for p in analysis.get("key_points", []))

    return f"""---
created: {date}
tags:
{tags_yaml}
---

# {analysis["title"]}

{analysis["summary"]}

## Key Points
{key_points}

## Source
[Original Reel]({job["url"]}) — @{job["metadata"].get("uploader", "unknown")}
[[{raw_path}|Raw note]]
"""


async def route_to_obsidian(
    job: dict,
    intent: str,
    project: str = "",
    extra: str = "",
) -> dict:
    """
    Route a processed reel to the appropriate Obsidian location based on intent.

    Intents:
    - catalog     → raw/ note + wiki/ synthesis
    - try_this    → raw/ note + appended entry in Try-This-List.md
    - implement   → raw/ note + task appended to project TODO.md (or Inbox TODO)
    - inbox       → raw/ note + lightweight inbox note for later routing
    """
    analysis = job["analysis"]
    date = job["timestamp"][:10]
    safe_title = _safe_filename(analysis["title"])

    # Always write the raw note
    raw_path = f"{VAULT_RAW_FOLDER}/{date}-{safe_title}.md"
    raw_content = _build_raw_note(job)
    await write_note(raw_path, raw_content)

    if intent == "catalog":
        wiki_path = f"{VAULT_WIKI_FOLDER}/{safe_title}.md"
        wiki_content = _build_wiki_note(job, raw_path)
        await write_note(wiki_path, wiki_content)
        return {
            "status": "done",
            "message": f"Cataloged: \"{analysis['title']}\"",
            "paths": [raw_path, wiki_path],
        }

    elif intent == "try_this":
        entry = (
            f"\n## {analysis['title']}\n"
            f"*Added {date}*\n\n"
            f"{analysis['summary']}\n\n"
            f"[[{raw_path}|Source reel]]\n"
        )
        await append_to_note(VAULT_TRY_THIS_NOTE, entry)
        return {
            "status": "done",
            "message": f"Added to Try-This list: \"{analysis['title']}\"",
            "paths": [raw_path, VAULT_TRY_THIS_NOTE],
        }

    elif intent == "implement":
        if project:
            todo_path = f"02-Projects/{project}/TODO.md"
            label = project
        else:
            todo_path = f"{VAULT_INBOX_FOLDER}/TODO.md"
            label = "Inbox"
        summary_short = analysis["summary"][:120].rstrip()
        task_entry = (
            f"\n- [ ] **[Reel]** {analysis['title']} — "
            f"{summary_short}{'...' if len(analysis['summary']) > 120 else ''} "
            f"([[{raw_path}|source]])\n"
        )
        await append_to_note(todo_path, task_entry)
        return {
            "status": "done",
            "message": f"Task added to {label} TODO",
            "paths": [raw_path, todo_path],
        }

    else:  # inbox — save it and route later
        inbox_path = f"{VAULT_INBOX_FOLDER}/{date}-{safe_title}.md"
        inbox_content = (
            f"# {analysis['title']}\n\n"
            f"*Saved {date} — needs routing*\n\n"
            f"{analysis['summary']}\n\n"
            f"**Suggested intent:** {analysis.get('suggested_intent', 'unknown')}\n"
            f"**Reason:** {analysis.get('intent_reason', '')}\n\n"
            f"[[{raw_path}|Raw note]]\n"
        )
        await write_note(inbox_path, inbox_content)
        return {
            "status": "done",
            "message": f"Saved to inbox: \"{analysis['title']}\"",
            "paths": [raw_path, inbox_path],
        }
