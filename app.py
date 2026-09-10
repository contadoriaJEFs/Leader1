import streamlit as st
import pandas as pd
from scraper.maps import search_google_maps
from scraper.website import enrich_lead
from scraper.normalizer import deduplicate_leads
from utils.exporter import leads_to_json, leads_to_csv
from utils.logger import get_logger

st.set_page_config(page_title="Lead Scraper Local", page_icon="🔎", layout="wide")

logger = get_logger()

st.title("🔎 Gerador de Leads Locais")
st.caption("Pesquisa pública de empresas e enriquecimento básico de dados. Não contorna CAPTCHAs ou mecanismos anti-bot.")

with st.sidebar:
    st.header("Parâmetros")
    niche = st.text_input("Nicho / termo de busca", "Escritório de Advocacia")
    city = st.text_input("Cidade", "Recife")
    state = st.text_input("UF", "PE")
    quantity = st.number_input("Quantidade", min_value=1, max_value=100, value=5, step=1)
    enrich = st.checkbox("Tentar encontrar WhatsApp e Instagram no site", value=True)

if "leads" not in st.session_state:
    st.session_state.leads = []

if st.button("🔎 Iniciar busca", type="primary"):
    if not niche.strip() or not city.strip():
        st.error("Informe o nicho e a cidade.")
        st.stop()

    progress = st.progress(0)
    status = st.empty()

    try:
        status.info("Abrindo a pesquisa...")
        raw = search_google_maps(niche.strip(), city.strip(), state.strip(), int(quantity))
        progress.progress(35)

        status.info(f"{len(raw)} resultados encontrados. Normalizando...")
        leads = deduplicate_leads(raw)
        progress.progress(50)

        if enrich:
            total = len(leads)
            for i, lead in enumerate(leads):
                status.info(f"Enriquecendo {i+1}/{total}: {lead.get('nome', '')}")
                try:
                    leads[i] = enrich_lead(lead)
                except Exception as exc:
                    logger.exception("Erro no enriquecimento: %s", exc)
                progress.progress(50 + int(((i + 1) / max(total, 1)) * 45))

        st.session_state.leads = leads
        progress.progress(100)
        status.success(f"Concluído: {len(leads)} lead(s).")
    except Exception as exc:
        logger.exception("Erro geral: %s", exc)
        st.error(f"Não foi possível concluir a busca: {exc}")

leads = st.session_state.leads

if leads:
    df = pd.DataFrame(leads)
    preferred = ["nome", "cidade", "estado", "endereco", "telefone", "whatsapp", "website", "instagram"]
    cols = [c for c in preferred if c in df.columns]
    df = df[cols]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Leads", len(df))
    c2.metric("Sites", int(df["website"].notna().sum()) if "website" in df else 0)
    c3.metric("WhatsApp", int(df["whatsapp"].notna().sum()) if "whatsapp" in df else 0)
    c4.metric("Instagram", int(df["instagram"].notna().sum()) if "instagram" in df else 0)

    st.dataframe(df, use_container_width=True, hide_index=True)

    st.download_button(
        "⬇️ Exportar JSON",
        data=leads_to_json(leads),
        file_name=f"leads_{city.lower().replace(' ', '_')}.json",
        mime="application/json",
    )

    st.download_button(
        "⬇️ Exportar CSV",
        data=leads_to_csv(leads),
        file_name=f"leads_{city.lower().replace(' ', '_')}.csv",
        mime="text/csv",
    )
else:
    st.info("Preencha os parâmetros e clique em “Iniciar busca”.")
