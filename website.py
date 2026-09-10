import re
from urllib.parse import urljoin, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}


def _clean_url(url):
    if not url:
        return None
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        return None
    return url.rstrip("/")


def _whatsapp_from_text(text):
    if not text:
        return None

    patterns = [
        r'https?://(?:www\.)?wa\.me/(\d{8,15})',
        r'https?://api\.whatsapp\.com/send\?[^\s"\'<>]*phone=(\d{8,15})',
        r'whatsapp://send\?[^\s"\'<>]*phone=(\d{8,15})',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return f"https://wa.me/{match.group(1)}"

    return None


def _instagram_from_text(text):
    if not text:
        return None

    pattern = r'https?://(?:www\.)?instagram\.com/([A-Za-z0-9._-]+)(?:[/?#][^\s"\'<>]*)?'

    for match in re.finditer(pattern, text, re.I):
        username = match.group(1).lower()
        if username not in {"p", "reel", "reels", "stories", "explore", "accounts"}:
            return f"https://www.instagram.com/{match.group(1)}"

    return None


def _extract_social(html):
    whatsapp = _whatsapp_from_text(html)
    instagram = _instagram_from_text(html)

    soup = BeautifulSoup(html, "html.parser")

    values = []
    for tag in soup.find_all(True):
        for key, value in tag.attrs.items():
            if isinstance(value, list):
                value = " ".join(map(str, value))
            if isinstance(value, str):
                values.append(value)

    for value in values:
        if not whatsapp:
            whatsapp = _whatsapp_from_text(value)
        if not instagram:
            instagram = _instagram_from_text(value)
        if whatsapp and instagram:
            break

    return whatsapp, instagram, soup


def _internal_candidates(base_url, soup):
    base = urlparse(base_url)
    candidates = []

    keywords = (
        "contato", "contact", "fale", "about", "sobre", "empresa", "atendimento"
    )

    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "").strip()
        label = anchor.get_text(" ", strip=True).lower()

        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)

        if parsed.scheme not in ("http", "https") or parsed.netloc != base.netloc:
            continue

        haystack = f"{label} {parsed.path}".lower()
        if any(word in haystack for word in keywords):
            if absolute.rstrip("/") != base_url.rstrip("/") and absolute not in candidates:
                candidates.append(absolute)

        if len(candidates) >= 3:
            break

    return candidates


def enrich_lead(lead):
    result = dict(lead)
    website = _clean_url(result.get("website"))

    if not website:
        result.setdefault("whatsapp", None)
        result.setdefault("instagram", None)
        return result

    result["website"] = website
    result.setdefault("whatsapp", None)
    result.setdefault("instagram", None)

    visited = set()
    queue = [website]

    while queue and len(visited) < 4 and not (result.get("whatsapp") and result.get("instagram")):
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)

        try:
            response = requests.get(
                url,
                headers=HEADERS,
                timeout=10,
                allow_redirects=True,
            )
            response.raise_for_status()
            html = response.text[:3_000_000]
        except Exception:
            continue

        whatsapp, instagram, soup = _extract_social(html)

        if not result.get("whatsapp") and whatsapp:
            result["whatsapp"] = whatsapp
        if not result.get("instagram") and instagram:
            result["instagram"] = instagram

        if len(visited) == 1:
            queue.extend(_internal_candidates(response.url, soup))

    return result
