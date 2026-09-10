import streamlit as st
import pandas as pd

from maps import search_google_maps
from website import enrich_lead
from normalizer import deduplicate_leads, merge_leads
from exporter import leads_to_json, leads_to_csv
from logger import get_logger

st.set_page_config(page_title="Leader1 - Gerador de Leads", page_icon="🔎", layout="wide")
logger = get_logger()

st.title("🔎 Leader1 — Gerador de Leads")
st.caption("Pesquisa, enriquecimento e consolidação de empresas locais.")

if "search_leads" not in st.session_state:
    st.session_state.search_leads = []
if "base_leads" not in st.session_state:
    st.session_state.base_leads = []
if "requested" not in st.session_state:
    st.session_state.requested = 15

with st.sidebar:
    st.header("🔎 Nova pesquisa")

    niche = st.text_input("Nicho / termo", "Academias")
    city = st.text_input("Cidade", "Recife")
    state = st.text_input("UF", "PE")

    quantity = st.number_input(
        "Quantidade de novos leads",
        min_value=1,
        max_value=100,
        value=15,
        step=1,
    )

    st.divider()

    st.header("📂 Base existente")

    uploaded = st.file_uploader(
        "Importar JSON",
        type=["json"],
        accept_multiple_files=True,
        help="Você pode importar uma ou várias bases JSON."
    )

    ignore_existing = st.checkbox(
        "Ignorar empresas já existentes",
        value=True,
        help="Quando marcado, a pesquisa tenta retornar somente empresas novas."
    )

    if uploaded:
        import json

        imported = []

        for file in uploaded:
            try:
                data = json.load(file)

                if isinstance(data, list):
                    imported.extend(data)
                elif isinstance(data, dict):
                    imported.append(data)

            except Exception as exc:
                st.error(f"Erro ao ler {file.name}: {exc}")

        st.session_state.base_leads = deduplicate_leads(imported)

        st.success(
            f"{len(st.session_state.base_leads)} empresa(s) "
            "única(s) na base carregada."
        )

if st.button("🔎 Iniciar pesquisa", type="primary"):
    progress = st.progress(0)
    status = st.empty()

    try:
        requested = int(quantity)
        st.session_state.requested = requested

        status.info(
            f"Coletando resultados para {niche} — "
            f"{city}/{state}..."
        )

        raw = search_google_maps(
            niche.strip(),
            city.strip(),
            state.strip(),
            requested,
            progress_callback=lambda current, target: progress.progress(
                min(45, max(1, int(current / max(target, 1) * 45)))
            ),
        )

        collected = deduplicate_leads(raw)

        # Remove registros que já estão na base, quando solicitado.
        if ignore_existing and st.session_state.base_leads:
            new_leads, existing = merge_leads(
                st.session_state.base_leads,
                collected,
                return_new=True,
            )
            collected = new_leads
            status.info(
                f"Coleta: {len(raw)} | Novos: {len(collected)} | "
                f"Já existentes: {len(existing)}"
            )

        st.session_state.search_leads = collected
        progress.progress(50)

        if not collected:
            status.warning("Nenhum lead novo foi encontrado.")
            st.stop()

        # Enriquecimento somente dos leads que serão apresentados.
        total = len(collected)

        for i, lead in enumerate(collected):
            status.info(
                f"Enriquecendo {i + 1}/{total}: "
                f"{lead.get('nome') or 'empresa'}"
            )

            try:
                collected[i] = enrich_lead(lead)
            except Exception as exc:
                logger.exception("Erro no enriquecimento: %s", exc)

            st.session_state.search_leads = collected
            progress.progress(
                50 + int(((i + 1) / total) * 50)
            )

        status.success(
            f"Pesquisa concluída: {len(collected)} novo(s) lead(s)."
        )

    except Exception as exc:
        logger.exception("Erro na pesquisa: %s", exc)
        st.error(str(exc))

search_leads = st.session_state.search_leads
base_leads = st.session_state.base_leads

if search_leads:
    st.subheader("📌 Resultados da pesquisa atual")

    df = pd.DataFrame(search_leads)

    columns = [
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

    columns = [c for c in columns if c in df.columns]
    df = df[columns]

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    c1.metric("Solicitados", st.session_state.requested)
    c2.metric("Novos", len(df))
    c3.metric(
        "Telefones",
        int(df["telefone"].notna().sum()) if "telefone" in df else 0
    )
    c4.metric(
        "Horários",
        int(df["horario_funcionamento"].notna().sum())
        if "horario_funcionamento" in df else 0
    )
    c5.metric(
        "WhatsApp",
        int(df["whatsapp"].notna().sum()) if "whatsapp" in df else 0
    )
    c6.metric(
        "Instagram",
        int(df["instagram"].notna().sum()) if "instagram" in df else 0
    )

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "website": st.column_config.LinkColumn(
                "Website", display_text="Abrir site"
            ),
            "whatsapp": st.column_config.LinkColumn(
                "WhatsApp", display_text="Abrir WhatsApp"
            ),
            "instagram": st.column_config.LinkColumn(
                "Instagram", display_text="Abrir Instagram"
            ),
        },
    )

    st.markdown("### Exportar")

    b1, b2 = st.columns(2)

    with b1:
        st.download_button(
            "⬇️ JSON da pesquisa",
            leads_to_json(search_leads),
            "leads_pesquisa.json",
            "application/json",
        )

    with b2:
        st.download_button(
            "⬇️ CSV da pesquisa",
            leads_to_csv(search_leads),
            "leads_pesquisa.csv",
            "text/csv",
        )

# Consolidação
if base_leads or search_leads:
    st.divider()
    st.subheader("🗂️ Base consolidada")

    consolidated = merge_leads(
        base_leads,
        search_leads,
        return_new=False,
    )

    st.write(
        f"**Base anterior:** {len(base_leads)}  |  "
        f"**Pesquisa atual:** {len(search_leads)}  |  "
        f"**Consolidado sem duplicações:** {len(consolidated)}"
    )

    c1, c2 = st.columns(2)

    with c1:
        st.download_button(
            "⬇️ JSON consolidado",
            leads_to_json(consolidated),
            "leads_consolidado.json",
            "application/json",
        )

    with c2:
        st.download_button(
            "⬇️ CSV consolidado",
            leads_to_csv(consolidated),
            "leads_consolidado.csv",
            "text/csv",
        )
