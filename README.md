# Leader1 V3 — Gerador de Leads Locais

Aplicação Streamlit para pesquisa pública de empresas locais e enriquecimento básico.

## Estrutura

Todos os módulos ficam na raiz:

- `app.py` — interface
- `maps.py` — pesquisa e carregamento progressivo
- `website.py` — WhatsApp e Instagram
- `normalizer.py` — normalização e deduplicação
- `exporter.py` — JSON e CSV
- `logger.py` — logs
- `requirements.txt` — dependências Python
- `packages.txt` — Chromium e dependências do sistema

## Novidades da V3

- Tentativa de rolagem automática do painel de resultados.
- Busca até a quantidade solicitada, dentro dos resultados disponibilizados.
- Coluna `horario_funcionamento`.
- Proteção para não interpretar horários como telefone.
- Contadores de solicitados, encontrados e contatos.
- Links clicáveis para site, WhatsApp e Instagram.
- Aviso quando o Google disponibilizar menos resultados que o solicitado.

## Streamlit

Main file path:

`app.py`

## Teste recomendado

Nicho: Escritório de Advocacia

Cidade: Recife

UF: PE

Quantidade: 15

## Observação

A estrutura e os seletores do Google Maps podem mudar. A aplicação não resolve CAPTCHA, não faz login e não tenta contornar mecanismos de segurança.
