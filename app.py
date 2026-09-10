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
st.caption("Pesquisa pública de empresas e enriquecimento básico de dados.")

with st.sidebar:
    st.header("Pesquisa")
    niche = st.text_input("Nicho / termo", "Academias")
    city = st.text_input("Cidade", "Recife")
    state = st.text_input("UF", "PE")

    quantity = st.number_input(
        "Quantidade de leads",
        min_value=1,
        max_value=100,
        value=15,
        step=1,
        help="O sistema tenta carregar resultados até atingir a quantidade solicitada."
    )

    enrich = st.checkbox(
        "Pesquisar WhatsApp e Instagram no site",
        value=True
    )

if "leads" not in st.session_state:
    st.session_state.leads = []
if "requested" not in st.session_state:
    st.session_state.requested = 0

if st.button("🔎 Iniciar busca", type="primary"):
    if not niche.strip() or not city.strip():
        st.error("Informe o nicho e a cidade.")
        st.stop()

    progress = st.progress(0)
    status = st.empty()

    try:
        requested = int(quantity)
        st.session_state.requested = requested

        status.info(
            f"Coletando resultados: até {requested} "
            f"para {niche} em {city}/{state}..."
        )

        # ETAPA 1: somente coleta.
        leads = search_google_maps(
            niche.strip(),
            city.strip(),
            state.strip(),
            requested,
            progress_callback=lambda current, target: progress.progress(
                min(50, max(1, int(current / max(target, 1) * 50)))
            ),
        )

        # Deduplicação antes do enriquecimento.
        leads = deduplicate_leads(leads)
        st.session_state.leads = leads
        progress.progress(50)

        status.success(
            f"Coleta concluída: {len(leads)} de {requested} "
            f"resultado(s) solicitados."
        )

        # ETAPA 2: enriquecimento.
        if enrich and leads:
            status.info("Iniciando enriquecimento dos dados...")
            total = len(leads)

            for i, lead in enumerate(leads):
                status.info(
                    f"Enriquecendo {i + 1}/{total}: "
                    f"{lead.get('nome') or 'empresa'}"
                )

                try:
                    leads[i] = enrich_lead(lead)
                except Exception as exc:
                    logger.exception(
                        "Erro no enriquecimento: %s", exc
                    )

                st.session_state.leads = leads
                progress.progress(
                    50 + int(((i + 1) / total) * 50)
                )

            status.success(
                f"Processamento concluído: {len(leads)} lead(s)."
            )

    except Exception as exc:
        logger.exception("Erro na busca: %s", exc)
        st.error(str(exc))

leads = st.session_state.leads

if leads:
    df = pd.DataFrame(leads)

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

    requested = st.session_state.get("requested", len(df))

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Solicitados", requested)
    c2.metric("Coletados", len(df))
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

    if len(df) < requested:
        st.warning(
            f"A coleta retornou {len(df)} resultado(s), "
            f"embora tenham sido solicitados {requested}. "
            "Isso significa que a rolagem chegou ao limite disponível "
            "ou que o Maps não carregou novos resultados."
        )
    else:
        st.success(
            f"Quantidade atingida: {len(df)} resultado(s) coletados."
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
