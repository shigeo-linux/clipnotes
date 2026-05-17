import re
from datetime import date


def summary_to_markdown(summary_text, video_title='', channel='', url=''):
    """Convert a Clipnotes summary to Obsidian-compatible Markdown."""
    today = date.today().isoformat()

    # Build YAML frontmatter
    frontmatter = ['---']
    if channel:
        frontmatter.append(f'channel: "{channel}"')
    if url:
        frontmatter.append(f'source: "{url}"')
    frontmatter.append(f'date: {today}')
    frontmatter.append('tags: [youtube, clipnotes]')
    frontmatter.append('---')
    frontmatter_str = '\n'.join(frontmatter)

    # Convert summary body to clean Markdown
    lines = []
    body_started = False
    for line in summary_text.split('\n'):
        stripped = line.strip()

        # Skip the Source:/Channel: header lines — they're in the frontmatter
        if stripped.startswith('Source:') or stripped.startswith('Channel:'):
            continue

        # Bold title → H1
        if stripped.startswith('**') and stripped.endswith('**'):
            content = stripped.strip('*').strip()
            lines.append(f'# {content}')
            body_started = True
            continue

        # Bullet points — normalise to Markdown dash
        if stripped.startswith('•'):
            content = stripped.lstrip('• ').strip()
            if not body_started:
                lines.append('## Key Points')
                body_started = True
            lines.append(f'- {content}')
            continue

        lines.append(stripped)

    body = '\n'.join(lines).strip()
    return f'{frontmatter_str}\n\n{body}\n'


def safe_filename(title):
    """Convert a video title to a safe filename."""
    safe = re.sub(r'[<>:"/\\|?*]', '', title)
    safe = re.sub(r'\s+', ' ', safe).strip()
    return (safe[:80] or 'clipnotes_summary') + '.md'
