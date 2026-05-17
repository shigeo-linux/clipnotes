# Clipnotes

An AI-powered YouTube video summariser for Linux. Paste any YouTube URL, fetch the transcript, and generate a clean one-page summary with 5–10 key points — powered by your choice of AI model via OpenRouter. Save summaries as PDF, TXT, or directly to your Obsidian vault.

---

## Features

- **Instant summaries** — paste a YouTube URL, fetch the transcript, get a structured summary
- **5–10 key bullet points** — the most important insights from the video
- **Channel name and source URL** included in every summary
- **Save as PDF** — nicely formatted with title, overview, and bullet points
- **Save as TXT** — plain text export
- **Save to Obsidian** — saves a Markdown note with YAML frontmatter directly to your vault
- **Copy to clipboard** — paste your summary anywhere instantly
- **Large video support** — automatically chunks long transcripts and combines summaries
- **Model choice** — use Claude, GPT-4, Gemini, or any model available on OpenRouter

---

## Requirements

- Ubuntu 24.04 / Linux Mint 22.x (or any GTK3-capable Linux)
- Python 3.10+
- An OpenRouter API key (free tier available at [openrouter.ai/keys](https://openrouter.ai/keys))

---

## Installation

### Option 1 — Installer script (recommended)

```bash
cd clipnotes/
chmod +x install.sh
./install.sh
```

Then launch with:
```bash
clipnotes
```

Or search for **Clipnotes** in your application menu.

### Option 2 — Run directly without installing

Install dependencies:

```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 python3-requests

pip3 install --user youtube-transcript-api pypdf
```

Then run:

```bash
cd clipnotes/
python3 clipnotes.py
```

---

## First-time setup

1. Launch Clipnotes
2. Click **⚙ Settings** (top-right)
3. Enter your **OpenRouter API key**
4. Choose a model — Claude 3.5 Sonnet is recommended
5. Optionally set your **Obsidian vault path** for direct note saving
6. Click **Save**

---

## Usage

1. Paste a YouTube URL into the URL box and click **Fetch** (or press Enter)
2. Clipnotes fetches the transcript — no API key needed for this step
3. Click **Generate Summary**
4. For long videos, progress is shown (e.g. "Summarising part 2 of 3…")
5. Use **Copy**, **Save as TXT**, **Save as PDF**, or **Save to Obsidian**

---

## Obsidian integration

Set your vault folder path in Settings. When you click **Save to Obsidian**, Clipnotes saves a `.md` file directly into your vault with this format:

```markdown
---
channel: "Channel Name"
source: "https://youtube.com/watch?v=..."
date: 2026-05-17
tags: [youtube, clipnotes]
---

# Video Title

Overview paragraph...

- Key point 1
- Key point 2
```

The note appears in Obsidian immediately with no import needed.

---

## Recommended models (via OpenRouter)

| Model | Notes |
|---|---|
| `anthropic/claude-3.5-sonnet` | Best overall quality (default) |
| `openai/gpt-4o` | Strong alternative |
| `openai/gpt-4o-mini` | Faster, lower cost |
| `google/gemini-pro-1.5` | Long context window |

---

## Limitations

- Videos must have captions/transcripts enabled — auto-generated captions work for most English videos
- Private or age-restricted videos may not be accessible
- Non-English videos are supported if the video has captions in that language

---

## Data storage

| Data | Location |
|---|---|
| Settings & API key | `~/.config/clipnotes/config.json` |

---

## Troubleshooting

**"Could not fetch transcript"**
The video may have transcripts disabled, be private, or be age-restricted. Try a different video.

**"No API key configured"**
Open Settings (⚙) and enter your OpenRouter API key from [openrouter.ai/keys](https://openrouter.ai/keys).

**App won't start**
```bash
python3 /opt/clipnotes/clipnotes.py
```
Run from terminal to see error messages.

---

## Uninstall

```bash
sudo rm -rf /opt/clipnotes
sudo rm -f /usr/local/bin/clipnotes
sudo rm -f /usr/share/applications/clipnotes.desktop
sudo rm -f /usr/share/icons/hicolor/scalable/apps/clipnotes.svg
rm -rf ~/.config/clipnotes
```
