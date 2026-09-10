from urllib.parse import quote_plus
import re
import shutil
import os

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from logger import get_logger

logger = get_logger()

PHONE_RE = re.compile(
    r"(?<!\d)"
    r"(?:\+?55[\s.-]*)?"
    r"(?:\(?\d{2}\)?[\s.-]*)?"
    r"(?:9[\s.-]*)?\d{4}[\s.-]*\d{4}"
    r"(?!\d)"
)

TIME_RANGE_RE = re.compile(
    r"^\s*\d{1,2}[:h]\d{2}\s*(?:[-–—]|às|a)\s*\d{1,2}[:h]\d{2}\s*$",
    re.I,
)

DAY_RE = re.compile(
    r"\b(segunda|terça|terca|quarta|quinta|sexta|sábado|sabado|domingo)\b",
    re.I,
)

def _text(locator):
    try:
        value = locator.first.inner_text(timeout=2500)
        return value.strip() if value else ""
    except Exception:
        return ""

def _chromium_executable():
    for candidate in (
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome",
    ):
        if shutil.which(candidate) or os.path.exists(candidate):
            return candidate
    return None

def _looks_like_phone(value):
    if not value:
        return False

    value = value.strip()

    if TIME_RANGE_RE.match(value):
        return False

    digits = re.sub(r"\D", "", value)

    # Evita falsos positivos de horários e números muito curtos.
    if len(digits) not in (8, 9, 10, 11, 12, 13):
        return False

    return bool(PHONE_RE.search(value))

def _extract_phone(lines):
    for line in lines:
        if _looks_like_phone(line):
            match = PHONE_RE.search(line)
            if match:
                return match.group(0).strip()
    return None

def _is_hours_line(line):
    if not line:
        return False

    clean = re.sub(r"\s+", " ", line).strip()
    low = clean.lower()

    if TIME_RANGE_RE.match(clean):
        return True

    if DAY_RE.search(low):
        return True

    keywords = (
        "aberto",
        "fecha",
        "fechado",
        "horário",
        "horario",
        "24 horas",
    )

    return any(k in low for k in keywords) and not _looks_like_phone(clean)

def _extract_hours(lines):
    values = []

    for line in lines:
        clean = re.sub(r"\s+", " ", line).strip()

        if _is_hours_line(clean) and len(clean) <= 220:
            if clean not in values:
                values.append(clean)

    return " | ".join(values) if values else None

def _extract_address(lines):
    patterns = (
        r"\bRua\b", r"\bR\.", r"\bAvenida\b", r"\bAv\.",
        r"\bRodovia\b", r"\bEstrada\b", r"\bTravessa\b",
        r"\bPraça\b", r"\bPraia\b", r"\bAlameda\b",
        r"\bLadeira\b",
    )

    for line in lines:
        if any(re.search(pattern, line, re.I) for pattern in patterns):
            return line.strip()

    return None

def _current_count(page):
    try:
        return page.locator('div[role="article"]').count()
    except Exception:
        return 0

def _scroll_results(page, target, progress_callback=None):
    """
    Carrega progressivamente o feed do Google Maps.

    A rotina:
    - verifica a quantidade atual;
    - rola o feed;
    - aguarda o carregamento;
    - verifica novamente;
    - repete até atingir o alvo ou detectar que não há crescimento.
    """
    feed = page.locator('div[role="feed"]')

    best_count = _current_count(page)
    stagnant = 0

    # Para 15, por exemplo, são permitidas muitas tentativas.
    max_rounds = max(20, min(100, target * 5))

    for round_no in range(max_rounds):
        count = _current_count(page)

        if count > best_count:
            best_count = count
            stagnant = 0
        else:
            stagnant += 1

        if progress_callback:
            progress_callback(min(best_count, target), target)

        if best_count >= target:
            return best_count

        # Tenta rolar diretamente o feed e também com a roda do mouse.
        try:
            if feed.count() > 0:
                feed.first.hover(timeout=2500)
                page.mouse.wheel(0, 2200)
            else:
                page.mouse.wheel(0, 2200)
        except Exception:
            try:
                page.mouse.wheel(0, 3000)
            except Exception:
                pass

        # Tempo variável para permitir carregamento assíncrono.
        page.wait_for_timeout(1800)

        new_count = _current_count(page)

        if new_count > best_count:
            best_count = new_count
            stagnant = 0

        # Se ficou várias rodadas sem crescer, faz uma pausa maior
        # antes de concluir.
        if stagnant in (4, 8, 12):
            page.wait_for_timeout(3500)

        # Muitas rodadas sem qualquer crescimento: fim provável.
        if stagnant >= 16:
            break

    return best_count

def search_google_maps(
    niche,
    city,
    state,
    quantity=5,
    progress_callback=None,
):
    query = f"{niche} {city} {state}".strip()
    url = "https://www.google.com/maps/search/" + quote_plus(query)

    results = []

    with sync_playwright() as p:
        executable = _chromium_executable()

        launch_args = {
            "headless": True,
            "args": [
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
        }

        if executable:
            launch_args["executable_path"] = executable

        try:
            browser = p.chromium.launch(**launch_args)
        except Exception as exc:
            raise RuntimeError(
                "Não foi possível iniciar o Chromium no servidor."
            ) from exc

        page = browser.new_page(
            locale="pt-BR",
            viewport={"width": 1365, "height": 900},
        )

        try:
            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=45000,
            )
            page.wait_for_timeout(4500)

            body = page.locator("body").inner_text(timeout=5000).lower()

            if any(term in body for term in (
                "captcha",
                "unusual traffic",
                "não sou um robô",
                "verificação",
            )):
                raise RuntimeError(
                    "O Google apresentou uma verificação/CAPTCHA. "
                    "A aplicação não tenta contornar esse mecanismo."
                )

            _scroll_results(
                page,
                quantity,
                progress_callback=progress_callback,
            )

            cards = page.locator('div[role="article"]')
            count = min(cards.count(), quantity)

            for i in range(count):
                card = cards.nth(i)
                text = _text(card)

                lines = [
                    x.strip()
                    for x in text.splitlines()
                    if x.strip()
                ]

                nome = lines[0] if lines else None
                endereco = _extract_address(lines)
                telefone = _extract_phone(lines)
                horario = _extract_hours(lines)
                website = None

                try:
                    links = card.locator("a")

                    for j in range(links.count()):
                        link = links.nth(j)
                        href = link.get_attribute("href") or ""
                        label = (link.inner_text() or "").strip()

                        if href.startswith("tel:"):
                            candidate = href[4:].strip()

                            if _looks_like_phone(candidate):
                                telefone = candidate

                        elif (
                            href.startswith(("http://", "https://"))
                            and "google." not in href
                            and "goo.gl" not in href
                        ):
                            website = href

                        if not endereco:
                            address = _extract_address([label])
                            if address:
                                endereco = address

                except Exception:
                    pass

                results.append({
                    "nome": nome,
                    "cidade": city,
                    "estado": state,
                    "endereco": endereco,
                    "telefone": telefone,
                    "horario_funcionamento": horario,
                    "whatsapp": None,
                    "website": website,
                    "instagram": None,
                })

            # Fallback quando os cards não aparecem no DOM.
            if not results:
                links = page.locator('a[href*="/maps/place/"]')
                seen = set()

                for i in range(min(links.count(), quantity * 2)):
                    link = links.nth(i)

                    name_lines = (
                        link.inner_text() or ""
                    ).strip().splitlines()

                    href = link.get_attribute("href")

                    if (
                        name_lines
                        and href
                        and name_lines[0] not in seen
                    ):
                        seen.add(name_lines[0])

                        results.append({
                            "nome": name_lines[0],
                            "cidade": city,
                            "estado": state,
                            "endereco": None,
                            "telefone": None,
                            "horario_funcionamento": None,
                            "whatsapp": None,
                            "website": None,
                            "instagram": None,
                        })

                    if len(results) >= quantity:
                        break

        except PlaywrightTimeoutError:
            raise RuntimeError(
                "A pesquisa demorou demais para responder."
            )
        finally:
            browser.close()

    return results[:quantity]
