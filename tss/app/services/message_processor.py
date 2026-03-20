"""
Message processor service.
Determines whether a message is verbal or non-verbal and acts accordingly.

Non-verbal: message composed entirely of emojis, URLs, GIF links, mentions, or whitespace —
no actual words. Examples: "🎉🔥", "https://giphy.com/abc", "😂😂😂".
"""

import re

from app.services import session_cache

# Matches URLs (http/https/www)
_URL_RE = re.compile(r'https?://\S+|www\.\S+', re.IGNORECASE)

# Matches @mentions
_MENTION_RE = re.compile(r'@\w+')

# Matches emoji characters across the main Unicode emoji blocks
_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"  # Misc symbols, pictographs, transport, flags, people, etc.
    "\U00002600-\U000027BF"  # Misc symbols + dingbats
    "\U0001F1E0-\U0001F1FF"  # Regional indicator symbols (flags)
    "\U0000200D"             # Zero-width joiner (part of emoji sequences)
    "\U0000FE00-\U0000FE0F"  # Variation selectors
    "\U00002702-\U000027B0"
    "]+",
    flags=re.UNICODE,
)


def is_nonverbal(content: str) -> bool:
    """
    Returns True if the message contains no actual words —
    only emojis, URLs, mentions, and/or whitespace.
    """
    text = content
    text = _URL_RE.sub("", text)
    text = _MENTION_RE.sub("", text)
    text = _EMOJI_RE.sub("", text)
    text = text.strip()
    return len(text) == 0 and len(content.strip()) > 0


def process(content: str, user_id: int) -> bool:
    """
    Classify and handle the message.
    Returns True if the message is non-verbal.
    """
    if not is_nonverbal(content):
        return False

    score = session_cache.get_score(user_id)
    print(f"[NON-VERBAL] user_id={user_id} | vibe_score={score} | message={content!r}")
    return True
