import httpx
from config import OBSIDIAN_HOST, OBSIDIAN_API_KEY


def _auth_headers() -> dict:
    return {"Authorization": f"Bearer {OBSIDIAN_API_KEY}"}


def _write_headers() -> dict:
    return {
        "Authorization": f"Bearer {OBSIDIAN_API_KEY}",
        "Content-Type": "text/markdown",
    }


async def write_note(vault_path: str, content: str) -> bool:
    """
    Create or overwrite a note at vault_path.
    vault_path is relative to vault root, e.g. '07-Raw/reels/2026-05-19-my-note.md'
    """
    url = f"{OBSIDIAN_HOST}/vault/{vault_path}"
    async with httpx.AsyncClient(timeout=15, verify=False) as client:
        resp = await client.put(url, content=content.encode("utf-8"), headers=_write_headers())
        resp.raise_for_status()
    return True


async def read_note(vault_path: str) -> str | None:
    """
    Read an existing note. Returns None if not found.
    """
    url = f"{OBSIDIAN_HOST}/vault/{vault_path}"
    async with httpx.AsyncClient(timeout=10, verify=False) as client:
        resp = await client.get(url, headers=_auth_headers())
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.text


async def append_to_note(vault_path: str, content: str) -> bool:
    """
    Append content to an existing note. Creates the note if it doesn't exist.
    """
    existing = await read_note(vault_path)
    if existing is not None:
        new_content = existing.rstrip() + "\n\n" + content.lstrip()
    else:
        new_content = content
    return await write_note(vault_path, new_content)
