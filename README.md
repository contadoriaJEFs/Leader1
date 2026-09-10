# Leader1 — Gerador de Leads

Projeto Streamlit com todos os módulos na raiz do repositório.

## Estrutura

- app.py — aplicação principal
- maps.py — pesquisa
- website.py — WhatsApp e Instagram
- normalizer.py — normalização e deduplicação
- exporter.py — JSON e CSV
- logger.py — logs
- requirements.txt — dependências Python
- packages.txt — pacotes do sistema

## Streamlit

No Streamlit Community Cloud, use:

Main file path:
app.py

## Atenção ao Playwright

O projeto usa Playwright/Chromium para a pesquisa automatizada. O ambiente de hospedagem precisa disponibilizar o navegador Chromium.

A aplicação não resolve CAPTCHA, não faz login e não tenta contornar mecanismos anti-bot.

## Uso inicial

Nicho: Escritório de Advocacia
Cidade: Recife
UF: PE
Quantidade: 5

Depois clique em Iniciar busca.
