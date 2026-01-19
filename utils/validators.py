import re

def is_supported_url(text: str) -> bool:
    """
    Checks if the provided text contains a supported URL (YouTube, Instagram, TikTok).
    """
    if not text:
        return False
        
    # Regular expressions for supported domains
    youtube_regex = r"(?:https?:\/\/)?(?:www\.)?(?:youtube\.com|youtu\.be)\/(?:watch\?v=|shorts\/)?[\w-]+"
    instagram_regex = r"(?:https?:\/\/)?(?:www\.)?instagram\.com\/(?:p|reel|tv)\/[\w-]+"
    tiktok_regex = r"(?:https?:\/\/)?(?:www\.|vm\.|vt\.)?tiktok\.com\/.*"

    return bool(
        re.search(youtube_regex, text) or
        re.search(instagram_regex, text) or
        re.search(tiktok_regex, text)
    )

def extract_url(text: str) -> str | None:
    """
    Extracts the first supported URL from the text.
    """
    # A simple regex to catch http/https links, we trust yt-dlp to validate specific platform support deeper,
    # but initially we want to catch anything that looks like a URL if valid_supported is too strict.
    # However, to be strict as per requirements:
    
    youtube_regex = r"(?:https?:\/\/)?(?:www\.)?(?:youtube\.com|youtu\.be)\/(?:watch\?v=|shorts\/)?[\w-]+"
    instagram_regex = r"(?:https?:\/\/)?(?:www\.)?instagram\.com\/(?:p|reel|tv)\/[\w-]+"
    tiktok_regex = r"(?:https?:\/\/)?(?:www\.|vm\.|vt\.)?tiktok\.com\/[^\s]+"

    patterns = [youtube_regex, instagram_regex, tiktok_regex]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    return None
