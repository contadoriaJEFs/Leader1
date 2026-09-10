from urllib.parse import quote_plus
import re
import shutil

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from logger import get_logger

logger = get_logger()

def _text(locator):
    try:
        value = locator.first.inner_text(timeout=2500)
        return value.strip() if value else ""
    except Exception:
        return ""

def _chromium_executable():
    """
    Streamlit Community Cloud installs Linux packages from packages.txt.
    Prefer the system Chromium installed by apt; fall back to Playwright's
    bundled browser if it is available.
    """
    for candidate in (
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome",
    ):
        if shutil.which(candidate) or __import__("os").path.exists(candidate):
            return candidate
    return None

def search_google_maps(niche, city, state, quantity=5):
    query = f"{niche} {city} {state}".strip()
    url = "https://www.google.com/maps/search/" + quote_plus(query)

    results = []

    with sync_playwright() as p:
        executable = _chromium_executable()

        launch_args = {
            "headless": True,
            "args": ["--disable-dev-shm-usage", "--no-sandbox"],
        }

        if executable:
            launch_args["executable_path"] = executable

        try:
            browser = p.chromium.launch(**launch_args)
        except Exception as exc:
            raise RuntimeError(
                "Não foi possível iniciar o Chromium no servidor. "
                "Verifique se o pacote chromium foi instalado pelo Streamlit."
            ) from exc

        page = browser.new_page(
            locale="pt-BR",
            viewport={"width": 1365, "height": 900},
        )

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(4000)

            body = page.locator("body").inner_text(timeout=5000).lower()

            if any(term in body for term in [
                "captcha",
                "unusual traffic",
                "não sou um robô",
                "verificação"
            ]):
                raise RuntimeError(
                    "O Google apresentou uma verificação/CAPTCHA. "
                    "A aplicação não tenta contornar esse mecanismo."
                )

            cards = page.locator('div[role="article"]')
            count = min(cards.count(), quantity)

            for i in range(count):
                card = cards.nth(i)
                text = _text(card)
                lines = [x.strip() for x in text.splitlines() if x.strip()]

                nome = lines[0] if lines else None
                endereco = None
                telefone = None
                website = None

                try:
                    links = card.locator("a")
                    for j in range(links.count()):
                        link = links.nth(j)
                        href = link.get_attribute("href") or ""
                        label = (link.inner_text() or "").strip()

                        if href.startswith("tel:"):
                            telefone = href[4:].strip()
                        elif (
                            href.startswith(("http://", "https://"))
                            and "google." not in href
                            and "goo.gl" not in href
                        ):
                            website = href

                        if not endereco and re.search(
                            r"\b(Rua|R\.|Avenida|Av\.|Rodovia|Estrada|Travessa|Praça)\b",
                            label, re.I
                        ):
                            endereco = label
                except Exception:
                    pass

                for line in lines[1:]:
                    if not endereco and re.search(
                        r"\b(Rua|R\.|Avenida|Av\.|Rodovia|Estrada|Travessa|Praça)\b",
                        line, re.I
                    ):
                        endereco = line

                    if not telefone and re.search(
                        r"(\+?55\s?)?(\(?\d{2}\)?\s?)?\d{4,5}[-.\s]?\d{4}",
                        line
                    ):
                        telefone = line

                results.append({
                    "nome": nome,
                    "cidade": city,
                    "estado": state,
                    "endereco": endereco,
                    "telefone": telefone,
                    "whatsapp": None,
                    "website": website,
                    "instagram": None,
                })

            if not results:
                links = page.locator('a[href*="/maps/place/"]')
                seen = set()

                for i in range(min(links.count(), quantity * 2)):
                    link = links.nth(i)
                    name_lines = (link.inner_text() or "").strip().splitlines()
                    href = link.get_attribute("href")

                    if name_lines and href and name_lines[0] not in seen:
                        seen.add(name_lines[0])
                        results.append({
                            "nome": name_lines[0],
                            "cidade": city,
                            "estado": state,
                            "endereco": None,
                            "telefone": None,
                            "whatsapp": None,
                            "website": None,
                            "instagram": None,
                        })

                    if len(results) >= quantity:
                        break

        except PlaywrightTimeoutError:
            raise RuntimeError("A pesquisa demorou demais para responder.")
        finally:
            browser.close()

    return results[:quantity]
