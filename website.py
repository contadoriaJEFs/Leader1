import re
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

SOCIAL_HOSTS = {
    "instagram.com": "instagram",
    "www.instagram.com": "instagram",
}

def _normalize_url(url):
    if not url:
        return None
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url

def enrich_lead(lead):
    site = _normalize_url(lead.get("website"))
    if not site:
        return lead

    try:
        response = requests.get(
            site,
            timeout=12,
            headers={"User-Agent": "Mozilla/5.0 (compatible; LeadResearch/1.0)"},
            allow_redirects=True,
        )
        response.raise_for_status()

        final_url = response.url
        lead["website"] = final_url

        soup = BeautifulSoup(response.text, "html.parser")

        instagram = None
        whatsapp = None

        for a in soup.find_all("a", href=True):
            href = a.get("href", "").strip()
            low = href.lower()

            if not instagram and (
                "instagram.com/" in low
                and "instagram.com/p/" not in low
            ):
                instagram = href

            if not whatsapp and (
                "wa.me/" in low
                or "api.whatsapp.com/" in low
                or "web.whatsapp.com/" in low
            ):
                whatsapp = href

        if not whatsapp:
            # Procura também no HTML bruto por URLs de WhatsApp.
            match = re.search(
                r'https?://(?:api\.whatsapp\.com/send\?[^"\']+|wa\.me/\d+)',
                response.text,
                re.I,
            )
            if match:
                whatsapp = match.group(0)

        lead["whatsapp"] = whatsapp
        lead["instagram"] = instagram

    except Exception:
        # Um site indisponível não deve interromper os demais leads.
        pass

    return lead
