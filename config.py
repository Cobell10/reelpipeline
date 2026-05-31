import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Obsidian Local REST API
OBSIDIAN_HOST = os.getenv("OBSIDIAN_HOST", "http://localhost:27123")
OBSIDIAN_API_KEY = os.getenv("OBSIDIAN_API_KEY")

# Vault folder targets
VAULT_RAW_FOLDER = "07-Raw/reels"
VAULT_WIKI_FOLDER = "08-Wiki"
VAULT_INBOX_FOLDER = "09-Inbox"
VAULT_TRY_THIS_NOTE = "05-Personal/Try-This-List.md"

# GitHub queue repo (set on Render; leave unset for local direct-write mode)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_QUEUE_REPO = os.getenv("GITHUB_QUEUE_REPO")  # e.g. "cobell2429/reelpipeline-queue"

# Render URL (used by flush.py on the PC to reach the cloud server)
RENDER_URL = os.getenv("RENDER_URL", "http://localhost:8765")

# Server
SERVER_PORT = int(os.getenv("PORT", "8765"))
