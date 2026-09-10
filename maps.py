from urllib.parse import quote_plus
import re
import shutil
import os

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from logger import get_logger

logger = get_logger()

# Telefones brasileiros comuns. Horários como 08:00–18:00 são
# deliberadamente excluídos.
PHONE_RE = re.compile(
    r"(?<!\d)"
    r"(?:\+?55[\s.-]*)?"
    r"(?:\(?\d{2}\)?[\s.-]*)?"
    r"(?:9[\s.-]*)?\d{4}[\s.-]*\d{4}"
    r"(?!\d)"
)

TIME_RE = re.compile(
    r"^\s*(?:\d{1,2}[:h]\d{2})\s*(?:[-–—]|às|a)\s*"
    r"(?:\d{1,2}[:h]\d{2})\s*$",
    re.I
)

DAY_RE = re.compile(
    r"\b("
    r"segunda|terça|terca|quarta|quinta|sexta|sábado|sabado|domingo"
    r")\b",
    re.I
)

HOURS_KEYWORDS = (
    "aberto",
    "fecha",
    "fechado",
    "horário",
    "horario",
    "24 horas",
    "segunda",
    "terça",
    "terca",
    "quarta",
    "quinta",
    "sexta",
    "sábado",
    "sabado",
    "domingo",
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

    # Nunca tratar uma faixa de horário como telefone.
    if TIME_RE.match(value):
        return False

    # Evita capturar linhas puramente horárias.
    if re.search(r"\b(?:horas?|h)\b", value, re.I):
        return False

    match = PHONE_RE.search(value)
    if not match:
        return False

    digits = re.sub(r"\D", "", match.group(0))

    # Brasil: 10/11 dígitos com DDD; 8/9 podem aparecer localmente.
    return len(digits) in (8, 9, 10, 11, 12, 13)

def _extract_phone(lines):
    for line in lines:
        if _looks_like_phone(line):
            match = PHONE_RE.search(line)
            if match:
                return match.group(0).strip()
    return None

def _looks_like_hours(line):
    if not line:
        return False

    low = line.lower().strip()

    if DAY_RE.search(low):
        return True

    if any(keyword in low for keyword in HOURS_KEYWORDS):
        # Não aceitar uma linha que seja apenas um telefone.
        if not _looks_like_phone(line):
            return True

    # Faixas horárias isoladas, por exemplo 08:00–18:00.
    if TIME_RE.match(line):
        return True

    return False

def _extract_hours(lines):
    found = []

    for line in lines:
        clean = re.sub(r"\s+", " ", line).strip()

        if not clean:
            continue

        if _looks_like_hours(clean):
            # Evita transformar textos enormes do cartão em "horário".
            if len(clean) <= 180:
                found.append(clean)

    # Remove duplicados mantendo a ordem.
    unique = []
    seen = set()

    for item in found:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            unique.append(item)

    return " | ".join(unique) if unique else None

def _extract_address(lines):
    patterns = (
        r"\bRua\b",
        r"\bR\.",
        r"\bAvenida\b",
        r"\bAv\.",
        r"\bRodovia\b",
        r"\bEstrada\b",
        r"\bTravessa\b",
        r"\bPraça\b",
        r"\bPraia\b",
        r"\bAlameda\b",
        r"\bLadeira\b",
    )

    for line in lines:
        if any(re.search(pattern, line, re.I) for pattern in patterns):
            return line.strip()

    return None

def _scroll_results(page, target, progress_callback=None):
    """
    Rola o painel de resultados para forçar o carregamento progressivo.
    O Google Maps pode apresentar menos resultados do que o solicitado.
    """
    feed = page.locator('div[role="feed"]')

    previous_count = 0
    stagnant_rounds = 0

    # Limite de segurança: não ficar rolando indefinidamente.
    max_rounds = max(12, min(60, target * 3))

    for round_no in range(max_rounds):
        cards = page.locator('div[role="article"]')
        count = cards.count()

        if progress_callback:
            progress_callback(min(count, target), target)

        if count >= target:
            return count

        if count == previous_count:
            stagnant_rounds += 1
        else:
            stagnant_rounds = 0

        # Depois de algumas rodadas sem crescimento, ainda fazemos
        # algumas tentativas, pois o carregamento pode ser lento.
        if stagnant_rounds >= 5:
            break

        previous_count = count

        try:
            if feed.count() > 0:
                feed.last.hover(timeout=2000)
                page.mouse.wheel(0, 1800)
            else:
                page.mouse.wheel(0, 1800)

            page.wait_for_timeout(1800)
        except Exception:
            page.wait_for_timeout(1800)

    return page.locator('div[role="article"]').count()

def search_google_maps(
    niche,
    city,
    state,
    quantity=5,
    progress_callback=None
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
                timeout=45000
            )
            page.wait_for_timeout(4000)

            body = page.locator("body").inner_text(timeout=5000).lower()

            if any(term in body for term in [
                "captcha",
                "unusual traffic",
                "não sou um robô",
                "verificação",
            ]):
                raise RuntimeError(
                    "O Google apresentou uma verificação/CAPTCHA. "
                    "A aplicação não tenta contornar esse mecanismo."
                )

            _scroll_results(
                page,
                quantity,
                progress_callback=progress_callback
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

                        if not endereco and _extract_address([label]):
                            endereco = label

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

            # Fallback para páginas em que os cards não foram expostos.
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
