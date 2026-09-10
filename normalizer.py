import re

FIELDS = [
    "nome",
    "cidade",
    "estado",
    "endereco",
    "telefone",
    "horario_funcionamento",
    "whatsapp",
    "website",
    "instagram",
]

def normalize_phone(phone):
    if not phone:
        return None

    value = re.sub(r"\s+", " ", str(phone)).strip()

    # Segurança adicional contra horários.
    if re.fullmatch(
        r"\d{1,2}[:h]\d{2}\s*(?:[-–—]|às|a)\s*\d{1,2}[:h]\d{2}",
        value,
        re.I,
    ):
        return None

    return value or None

def normalize_lead(lead):
    result = {}

    for field in FIELDS:
        value = lead.get(field)

        if isinstance(value, str):
            value = value.strip()

        result[field] = value or None

    result["telefone"] = normalize_phone(
        result["telefone"]
    )

    return result

def deduplicate_leads(leads):
    output = []
    seen = set()

    for lead in leads:
        lead = normalize_lead(lead)

        key = (
            (lead["nome"] or "").lower(),
            (lead["endereco"] or "").lower(),
            re.sub(
                r"\D",
                "",
                lead["telefone"] or ""
            ),
        )

        if key in seen:
            continue

        seen.add(key)
        output.append(lead)

    return output
