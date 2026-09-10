import re
import requests
from bs4 import BeautifulSoup

def enrich_lead(lead):
    website = lead.get("website")

    if not website:
        return lead

    if not website.startswith(("http://", "https://")):
        website = "https://" + website

    try:
        response = requests.get(
            website,
            timeout=12,
            allow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; LeadResearch/1.0)"
                )
            },
        )
        response.raise_for_status()

        lead["website"] = response.url

        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup.find_all("a", href=True):
            href = tag["href"].strip()
            low = href.lower()

            if not lead.get("instagram") and "instagram.com/" in low:
                if "/p/" not in low and "/reel/" not in low:
                    lead["instagram"] = href

            if not lead.get("whatsapp") and (
                "wa.me/" in low
                or "api.whatsapp.com/" in low
                or "web.whatsapp.com/" in low
            ):
                lead["whatsapp"] = href

        if not lead.get("whatsapp"):
            match = re.search(
                r'https?://(?:wa\.me/\d+|api\.whatsapp\.com/send\?[^"\']+)',
                response.text,
                re.I,
            )

            if match:
                lead["whatsapp"] = match.group(0)

    except Exception:
        pass

    return lead
