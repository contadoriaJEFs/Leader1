import re

def normalize_phone(phone):
    if not phone:
        return None
    phone = re.sub(r'\s+', ' ', str(phone)).strip()
    return phone or None

def normalize_lead(lead):
    out = {
        "nome": (lead.get("nome") or "").strip() or None,
        "cidade": (lead.get("cidade") or "").strip() or None,
        "estado": (lead.get("estado") or "").strip() or None,
        "endereco": (lead.get("endereco") or "").strip() or None,
        "telefone": normalize_phone(lead.get("telefone")),
        "whatsapp": lead.get("whatsapp") or None,
        "website": lead.get("website") or None,
        "instagram": lead.get("instagram") or None,
    }
    return out

def deduplicate_leads(leads):
    output = []
    seen = set()

    for lead in leads:
        lead = normalize_lead(lead)
        key = (
            (lead["nome"] or "").lower(),
            (lead["endereco"] or "").lower(),
            re.sub(r"\D", "", lead["telefone"] or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        output.append(lead)

    return output
