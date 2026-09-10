from urllib.parse import quote_plus
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from utils.logger import get_logger

logger = get_logger()

def _first_text(locator):
    try:
        txt = locator.first.inner_text(timeout=2500)
        return txt.strip() if txt else None
    except Exception:
        return None

def search_google_maps(niche, city, state, quantity=5):
    """
    Coleta dados visíveis de resultados públicos do Google Maps.
    Não tenta resolver CAPTCHA, login ou outros mecanismos anti-bot.
    """
    query = f"{niche} {city} {state}".strip()
    url = "https://www.google.com/maps/search/" + quote_plus(query)

    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-dev-shm-usage", "--no-sandbox"]
        )
        page = browser.new_page(
            locale="pt-BR",
            viewport={"width": 1365, "height": 900},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            ),
        )

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(3500)

            body = (page.locator("body").inner_text(timeout=5000) or "").lower()
            if "captcha" in body or "unusual traffic" in body or "não sou um robô" in body:
                raise RuntimeError(
                    "O mecanismo de busca apresentou um CAPTCHA/bloqueio. "
                    "A aplicação não tenta contorná-lo."
                )

            # O Google Maps muda o DOM com frequência. Estes seletores são
            # deliberadamente simples e têm fallback por links / texto.
            cards = page.locator('div[role="article"]')
            count = min(cards.count(), quantity)

            for i in range(count):
                card = cards.nth(i)
                text = _first_text(card) or ""
                lines = [x.strip() for x in text.splitlines() if x.strip()]

                nome = lines[0] if lines else None
                endereco = None
                telefone = None
                website = None

                # Links do cartão
                try:
                    links = card.locator("a")
                    for j in range(links.count()):
                        a = links.nth(j)
                        href = a.get_attribute("href") or ""
                        label = (a.inner_text() or "").strip()

                        if href.startswith("tel:"):
                            telefone = href.replace("tel:", "").strip()
                        elif href.startswith("http") and "google." not in href:
                            website = href
                        elif label and any(k in label.lower() for k in ["rua ", "avenida ", "av. ", "rodovia ", "estrada "]):
                            endereco = label
                except Exception:
                    pass

                # Heurística simples para endereço e telefone no texto do cartão.
                import re
                for line in lines[1:]:
                    if not endereco and re.search(r'\b(Rua|Av\.?|Avenida|Rodovia|Estrada|R\.)\b', line, re.I):
                        endereco = line
                    if not telefone and re.search(r'(\+?55\s?)?(\(?\d{2}\)?\s?)?\d{4,5}[-.\s]?\d{4}', line):
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

            # Fallback: se role=article não funcionou, usa links de lugares.
            if not results:
                place_links = page.locator('a[href*="/maps/place/"]')
                seen = set()
                for i in range(min(place_links.count(), quantity * 2)):
                    a = place_links.nth(i)
                    name = (a.inner_text() or "").strip()
                    href = a.get_attribute("href")
                    if name and href and name not in seen:
                        seen.add(name)
                        results.append({
                            "nome": name.splitlines()[0].strip(),
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
            raise RuntimeError("A página demorou demais para responder.")
        finally:
            browser.close()

    return results[:quantity]
