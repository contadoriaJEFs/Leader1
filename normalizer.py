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

def _clean(value):
    if value is None:
        return None

    value = str(value).strip()

    return value or None

def normalize_phone(phone):
    value = _clean(phone)

    if not value:
        return None

    if re.fullmatch(
        r"\d{1,2}[:h]\d{2}\s*(?:[-–—]|às|a)\s*\d{1,2}[:h]\d{2}",
        value,
        re.I,
    ):
        return None

    return value

def normalize_url(url):
    value = _clean(url)

    if not value:
        return None

    value = value.rstrip("/")

    return value.lower()

def normalize_lead(lead):
    result = {}

    for field in FIELDS:
        result[field] = _clean(lead.get(field))

    result["telefone"] = normalize_phone(result["telefone"])

    return result

def _phone_key(phone):
    return re.sub(r"\D", "", phone or "")

def _domain_key(url):
    value = normalize_url(url)

    if not value:
        return ""

    value = re.sub(r"^https?://", "", value)
    value = value.split("/")[0]
    value = value.removeprefix("www.")

    return value

def _name_key(name):
    value = _clean(name)

    if not value:
        return ""

    value = value.lower()
    value = re.sub(r"[^a-z0-9áàâãéêíóôõúç ]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()

    # Termos jurídicos/societários comuns não devem ser o único
    # fator de diferenciação.
    value = re.sub(
        r"\b(ltda|me|eireli|epp|sa|s\.a\.)\b",
        "",
        value,
    )

    return re.sub(r"\s+", " ", value).strip()

def _identity_keys(lead):
    phone = _phone_key(lead.get("telefone"))
    domain = _domain_key(lead.get("website"))
    name = _name_key(lead.get("nome"))
    address = _name_key(lead.get("endereco"))
    city = _name_key(lead.get("cidade"))

    keys = []

    if phone:
        keys.append(("phone", phone))

    if domain:
        keys.append(("domain", domain))

    if name and address:
        keys.append(("name_address", name, address))

    if name and city:
        keys.append(("name_city", name, city))

    return keys

def same_lead(a, b):
    keys_a = set(_identity_keys(a))
    keys_b = set(_identity_keys(b))

    return bool(keys_a & keys_b)

def deduplicate_leads(leads):
    output = []

    for lead in leads:
        lead = normalize_lead(lead)

        duplicate_index = None

        for i, existing in enumerate(output):
            if same_lead(existing, lead):
                duplicate_index = i
                break

        if duplicate_index is None:
            output.append(lead)
        else:
            # O registro mais recente complementa campos ausentes.
            output[duplicate_index] = merge_two(
                output[duplicate_index],
                lead,
            )

    return output

def merge_two(old, new):
    result = dict(old)

    for field in FIELDS:
        old_value = result.get(field)
        new_value = new.get(field)

        if not old_value and new_value:
            result[field] = new_value

    return result

def merge_leads(base_leads, new_leads, return_new=False):
    """
    Consolida a base e a pesquisa atual.

    Quando return_new=True:
        retorna (somente_novos, existentes)

    Quando return_new=False:
        retorna a base consolidada.
    """
    base = deduplicate_leads(base_leads or [])
    new = deduplicate_leads(new_leads or [])

    consolidated = list(base)
    new_only = []
    existing = []

    for lead in new:
        found_index = None

        for i, old in enumerate(consolidated):
            if same_lead(old, lead):
                found_index = i
                break

        if found_index is None:
            consolidated.append(lead)
            new_only.append(lead)
        else:
            consolidated[found_index] = merge_two(
                consolidated[found_index],
                lead,
            )
            existing.append(lead)

    if return_new:
        return new_only, existing

    return consolidated
