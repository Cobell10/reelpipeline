# Reel Pipeline — Setup Guide

Share an Instagram Reel → Claude processes it → ShaBrain gets updated.

---

## How It Works

1. You hit **Share** on a Reel in Instagram
2. iOS Shortcut sends the URL to this server
3. Server downloads the audio (yt-dlp), transcribes it (Whisper API), analyzes it (Claude)
4. Shortcut shows you a summary + menu: **Catalog / Try This / Add to TODO / Inbox**
5. You tap one — notes are written directly to your Obsidian vault

Total time: ~30–60 seconds depending on reel length.

---

## Prerequisites

- Python 3.11+
- **ffmpeg** — required by yt-dlp for audio extraction
  - Download: https://ffmpeg.org/download.html (Windows build from gyan.dev)
  - Add `ffmpeg/bin` to your system PATH
- Obsidian with **Local REST API** plugin enabled (you already have this)
- OpenAI API key (for Whisper)
- Anthropic API key (for Claude summarization)
- **Tailscale** — so your iPhone can reach your PC from anywhere

---

## One-Time Setup

### 1. Install dependencies

```
cd reel-pipeline
pip install -r requirements.txt
```

### 2. Configure environment

```
copy .env.example .env
```

Edit `.env` and fill in:
- `OPENAI_API_KEY` — from platform.openai.com
- `ANTHROPIC_API_KEY` — from console.anthropic.com
- `OBSIDIAN_API_KEY` — from Obsidian → Settings → Local REST API → Copy API Key
- Leave everything else as defaults

### 3. Install Tailscale

- PC: https://tailscale.com/download/windows → install, sign in
- iPhone: App Store → Tailscale → install, sign in with **same account**
- Once both are connected, find your PC's Tailscale IP:
  - Open Tailscale on PC → hover over your machine name → copy the `100.x.x.x` IP
  - You'll use this IP in the iOS Shortcut

### 4. Create the vault folders in Obsidian

Create these folders if they don't exist yet:
- `07-Raw/reels/`
- `08-Wiki/`
- `09-Inbox/`
- `05-Personal/Try-This-List.md` (just create the file, leave it empty)

### 5. Start the server

```
python server.py
```

You should see: `Starting Reel Pipeline on port 8765`

To run it automatically on startup: create a Windows Task Scheduler task that runs
`python C:\path\to\reel-pipeline\server.py` at login.

---

## iOS Shortcut Setup

Create a new Shortcut in the Shortcuts app. Name it **"Send to ShaBrain"**.

Add these actions in order:

---

**Action 1: Receive input from Share Sheet**
- Input type: URLs
- Also accept: Text (in case the URL comes as plain text)

---

**Action 2: Ask for Input** *(optional — skip if you want zero friction)*
- Prompt: `Any notes? (optional)`
- Input type: Text
- Allow cancel: Yes
- Save result as: `UserNote`

---

**Action 3: Get Contents of URL**
- URL: `http://100.x.x.x:8765/process`  ← replace with your Tailscale IP
- Method: POST
- Headers:
  - `Content-Type`: `application/json`
- Request body: JSON
  ```json
  {
    "url": "[Shortcut Input]",
    "note": "[UserNote]"
  }
  ```
  Use the variable picker to insert `Shortcut Input` and `UserNote`.
- Save result as: `ProcessResult`

*(This step takes ~30–60 seconds. The spinner will show — that's normal.)*

---

**Action 4: Get Dictionary Value**
- Get value for key: `title`
- From: `ProcessResult`
- Save as: `ReelTitle`

**Action 5: Get Dictionary Value**
- Get value for key: `summary`  
- From: `ProcessResult`
- Save as: `ReelSummary`

**Action 6: Get Dictionary Value**
- Get value for key: `suggested_intent`
- From: `ProcessResult`
- Save as: `SuggestedIntent`

**Action 7: Get Dictionary Value**
- Get value for key: `process_id`
- From: `ProcessResult`
- Save as: `ProcessID`

---

**Action 8: Show Alert**
- Title: `[ReelTitle]`
- Message: `[ReelSummary]`
- *(This shows the summary so you know what you're routing)*

---

**Action 9: Choose from Menu**
- Prompt: `What do you want to do with this?`
- Options:
  - `Catalog it` (general knowledge, tutorial, tip)
  - `Try This` (recipe, activity, place to visit)
  - `Add to TODO` (actionable for a project)
  - `Inbox` (not sure yet — save and decide later)

For each menu option, add a **Get Contents of URL** action:
- URL: `http://100.x.x.x:8765/route`
- Method: POST
- Headers: `Content-Type: application/json`
- Body:
  - **Catalog it**: `{"process_id": "[ProcessID]", "intent": "catalog"}`
  - **Try This**: `{"process_id": "[ProcessID]", "intent": "try_this"}`
  - **Add to TODO**: `{"process_id": "[ProcessID]", "intent": "implement"}`
  - **Inbox**: `{"process_id": "[ProcessID]", "intent": "inbox"}`

---

**Action 10: Get Dictionary Value**
- Key: `message`
- From the route result
- Save as: `Confirmation`

**Action 11: Show Notification**
- Title: `ShaBrain`
- Body: `[Confirmation]`

---

## Usage

1. Open Instagram, find a Reel you want to save
2. Tap **Share → More → Send to ShaBrain**
3. Optionally type a note ("try this recipe", "for the CHClickTrack project", etc.)
4. Wait ~30–60 seconds for processing
5. Read the summary, pick your intent
6. Done — check Obsidian

---

## Intent Reference

| Choice | Where it goes |
|--------|--------------|
| **Catalog it** | `07-Raw/reels/` + `08-Wiki/` (full wiki page) |
| **Try This** | `07-Raw/reels/` + appended to `05-Personal/Try-This-List.md` |
| **Add to TODO** | `07-Raw/reels/` + task added to `02-Projects/<project>/TODO.md` or `09-Inbox/TODO.md` |
| **Inbox** | `07-Raw/reels/` + lightweight note in `09-Inbox/` |

---

## Troubleshooting

**"Job not found" error** — The server restarted between /process and /route. Re-share the reel.

**Shortcut times out** — The reel may be very long, or your connection is slow. Try again on WiFi.

**Empty transcript** — Some reels are music-only or have no speech. The summary will be based on the caption/description instead.

**ffmpeg not found** — Make sure `ffmpeg/bin` is in your system PATH. Restart the server after updating PATH.
