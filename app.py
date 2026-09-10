import streamlit as st
import pandas as pd

from maps import search_google_maps
from website import enrich_lead
from normalizer import deduplicate_leads
from exporter import leads_to_json, leads_to_csv
from logger import get_logger

st.set_page_config(page_title="Lead Scraper", page_icon="🔎", layout="wide")

logger = get_logger()

st.title("🔎 Gerador de Leads Locais")
st.write("Pesquisa pública de empresas e enriquecimento básico de dados.")

with st.sidebar:
    st.header("Pesquisa")
    niche = st.text_input("Nicho / termo", "Escritório de Advocacia")
    city = st.text_input("Cidade", "Recife")
    state = st.text_input("UF", "PE")
    quantity = st.number_input("Quantidade", 1, 100, 5)
    enrich = st.checkbox("Pesquisar WhatsApp e Instagram no site", True)

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
        leads = search_google_maps(
            niche.strip(), city.strip(), state.strip(), int(quantity)
        )
        progress.progress(40)

        leads = deduplicate_leads(leads)
        progress.progress(50)

        if enrich and leads:
            for i, lead in enumerate(leads):
                status.info(
                    f"Enriquecendo {i + 1}/{len(leads)}: "
                    f"{lead.get('nome') or 'empresa'}"
                )
                try:
                    leads[i] = enrich_lead(lead)
                except Exception as exc:
                    logger.exception("Erro no enriquecimento: %s", exc)
                progress.progress(50 + int(((i + 1) / len(leads)) * 50))

        st.session_state.leads = leads
        status.success(f"Busca concluída: {len(leads)} lead(s).")
        progress.progress(100)

    except Exception as exc:
        logger.exception("Erro na busca: %s", exc)
        st.error(str(exc))

leads = st.session_state.leads

if leads:
    df = pd.DataFrame(leads)

    columns = [
        "nome", "cidade", "estado", "endereco",
        "telefone", "whatsapp", "website", "instagram"
    ]
    columns = [c for c in columns if c in df.columns]
    df = df[columns]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Leads", len(df))
    c2.metric("Sites", int(df["website"].notna().sum()) if "website" in df else 0)
    c3.metric("WhatsApp", int(df["whatsapp"].notna().sum()) if "whatsapp" in df else 0)
    c4.metric("Instagram", int(df["instagram"].notna().sum()) if "instagram" in df else 0)

    st.dataframe(df, use_container_width=True, hide_index=True)

    st.download_button(
        "⬇️ Exportar JSON",
        leads_to_json(leads),
        f"leads_{city.lower().replace(' ', '_')}.json",
        "application/json",
    )

    st.download_button(
        "⬇️ Exportar CSV",
        leads_to_csv(leads),
        f"leads_{city.lower().replace(' ', '_')}.csv",
        "text/csv",
    )
else:
    st.info("Informe os parâmetros e clique em Iniciar busca.")
