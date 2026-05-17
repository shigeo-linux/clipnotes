import re
import json
import urllib.request

CHUNK_SIZE = 250_000


def extract_video_id(url):
    """Extract YouTube video ID from various URL formats."""
    url = url.strip()
    patterns = [
        r'(?:youtube\.com/watch\?v=)([a-zA-Z0-9_-]{11})',
        r'(?:youtu\.be/)([a-zA-Z0-9_-]{11})',
        r'(?:youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        r'(?:youtube\.com/shorts/)([a-zA-Z0-9_-]{11})',
    ]
    for pattern in patterns:
        m = re.search(pattern, url)
        if m:
            return m.group(1)
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
        return url
    return None


def get_video_info(video_id):
    """Fetch video title and channel via YouTube oEmbed (no API key needed)."""
    try:
        url = f'https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json'
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
            return data.get('title', ''), data.get('author_name', '')
    except Exception:
        return '', ''


def fetch_transcript(video_id):
    """
    Fetch transcript for a YouTube video using youtube-transcript-api v1.x.
    Returns (text, language, title, channel).
    """
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        raise RuntimeError("youtube-transcript-api not installed.\nRun: pip3 install --user youtube-transcript-api")

    title, channel = get_video_info(video_id)
    api = YouTubeTranscriptApi()

    # Try to list transcripts to find the best language
    lang_code = 'en'
    try:
        listing = api.list(video_id)
        # Prefer English, fall back to first available
        available = list(listing)
        if not available:
            raise RuntimeError("No transcripts available for this video.")
        lang_code = next(
            (t.language_code for t in available if t.language_code.startswith('en')),
            available[0].language_code
        )
    except Exception as e:
        if 'No transcripts' in str(e) or 'disabled' in str(e).lower():
            raise RuntimeError(f"Transcripts are disabled or unavailable for this video.\n{e}")
        # If listing fails, try fetching directly anyway
        pass

    try:
        result = api.fetch(video_id)
        data = list(result)
    except Exception as e:
        raise RuntimeError(f"Could not download transcript: {e}")

    if not data:
        raise RuntimeError("Transcript is empty.")

    text = ' '.join(entry.text.replace('\n', ' ') for entry in data).strip()
    return text, lang_code, title, channel


def split_chunks(text):
    return [text[i:i + CHUNK_SIZE] for i in range(0, len(text), CHUNK_SIZE)]
