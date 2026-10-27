import re
from typing import Optional
from urllib.parse import urlparse, parse_qs


# Regular expressions for YouTube URL variations
YOUTUBE_PATTERNS = [
    re.compile(r'(?:https?:\/\/)?(?:www\.|m\.)?youtube\.com\/watch\?.*v=([a-zA-Z0-9_-]{11})', re.IGNORECASE),
    re.compile(r'(?:https?:\/\/)?youtu\.be\/([a-zA-Z0-9_-]{11})', re.IGNORECASE),
    re.compile(r'(?:https?:\/\/)?(?:www\.)?youtube(?:-nocookie)?\.com\/embed\/([a-zA-Z0-9_-]{11})', re.IGNORECASE),
    re.compile(r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/v\/([a-zA-Z0-9_-]{11})', re.IGNORECASE),
    re.compile(r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})', re.IGNORECASE),
]

# Regular expressions for Vimeo URL variations
VIMEO_PATTERNS = [
    re.compile(r'(?:https?:\/\/)?(?:www\.)?vimeo\.com\/channels\/(?:[a-zA-Z0-9_-]+)\/(\d+)', re.IGNORECASE),
    re.compile(r'(?:https?:\/\/)?(?:www\.)?vimeo\.com\/groups\/(?:[a-zA-Z0-9_-]+)\/videos\/(\d+)', re.IGNORECASE),
    re.compile(r'(?:https?:\/\/)?(?:www\.)?vimeo\.com\/manage\/videos\/(\d+)', re.IGNORECASE),
    re.compile(r'(?:https?:\/\/)?player\.vimeo\.com\/video\/(\d+)', re.IGNORECASE),
    re.compile(r'(?:https?:\/\/)?(?:www\.)?vimeo\.com\/(\d+)', re.IGNORECASE),
]


def extract_youtube_id(url: str) -> Optional[str]:
    """
    Extracts the 11-character YouTube video ID from various share, embed,
    mobile, shorts, or standard watch URLs.
    """
    if not url:
        return None
    
    url = url.strip()
    
    # Check if raw 11-character ID was provided directly
    if re.fullmatch(r'[a-zA-Z0-9_-]{11}', url):
        return url

    # Try query parameters if it's a standard URL
    try:
        parsed = urlparse(url)
        if 'youtube.com' in parsed.netloc.lower():
            qs = parse_qs(parsed.query)
            if 'v' in qs and len(qs['v']) > 0 and len(qs['v'][0]) == 11:
                return qs['v'][0]
    except Exception:
        pass

    # Test regex patterns
    for pattern in YOUTUBE_PATTERNS:
        match = pattern.search(url)
        if match:
            return match.group(1)

    return None


def extract_vimeo_id(url: str) -> Optional[str]:
    """
    Extracts the numeric Vimeo video ID from various Vimeo URLs.
    """
    if not url:
        return None

    url = url.strip()

    # Check if numeric ID provided directly
    if re.fullmatch(r'\d{6,14}', url):
        return url

    # Test regex patterns
    for pattern in VIMEO_PATTERNS:
        match = pattern.search(url)
        if match:
            return match.group(1)

    return None


def detect_video_source(url: str = "", has_file: bool = False) -> str:
    """
    Detects video source ('youtube', 'vimeo', or 'mp4') based on URL or file attachment.
    """
    if has_file:
        return 'mp4'

    if not url:
        return 'youtube'

    cleaned = url.strip().lower()
    if 'youtube' in cleaned or 'youtu.be' in cleaned:
        return 'youtube'
    if 'vimeo' in cleaned:
        return 'vimeo'
    if (
        cleaned.endswith(('.mp4', '.webm', '.ogg', '.m4v'))
        or '.mp4' in cleaned
        or '/video/' in cleaned
        or '/clips/' in cleaned
        or '/stream/' in cleaned
    ):
        return 'mp4'

    return 'youtube'


def build_embed_url(source_type: str, url: str, video_id: Optional[str] = None, autoplay: bool = False) -> str:
    """
    Builds a secure, responsive iframe embed URL or direct file source URL.
    """
    if not url and not video_id:
        return ""

    if source_type == 'youtube':
        vid = video_id or extract_youtube_id(url)
        if vid:
            base = f"https://www.youtube-nocookie.com/embed/{vid}"
            params = ["rel=0"]
            if autoplay:
                params.append("autoplay=1")
            return f"{base}?{'&'.join(params)}"
        return url

    elif source_type == 'vimeo':
        vid = video_id or extract_vimeo_id(url)
        if vid:
            base = f"https://player.vimeo.com/video/{vid}"
            params = ["dnt=1"]
            if autoplay:
                params.append("autoplay=1")
            return f"{base}?{'&'.join(params)}"
        return url

    elif source_type == 'mp4':
        return url

    return url


def build_thumbnail_url(source_type: str, url: str = "", video_id: Optional[str] = None) -> Optional[str]:
    """
    Derives standard high-resolution thumbnail URL for supported providers (e.g. YouTube).
    """
    if source_type == 'youtube':
        vid = video_id or extract_youtube_id(url)
        if vid:
            return f"https://img.youtube.com/vi/{vid}/hqdefault.jpg"
    return None
