# Leader1 V5

Gerador de leads locais com pesquisa, enriquecimento e base histórica.

## Recursos

- Pesquisa de empresas no Google Maps.
- Carregamento progressivo do painel de resultados.
- Quantidade solicitada de 1 a 100.
- Telefone separado do horário de funcionamento.
- Enriquecimento básico de WhatsApp e Instagram a partir do site.
- Importação de um ou vários JSON.
- Deduplicação da base.
- Pesquisa somente de novos leads.
- Consolidação da base antiga com a pesquisa atual.
- Complementação de campos vazios quando uma pesquisa nova traz informação adicional.
- JSON da pesquisa.
- JSON consolidado.
- CSV da pesquisa.
- CSV consolidado.

## Estrutura

Todos os módulos ficam na raiz:

- app.py
- maps.py
- website.py
- normalizer.py
- exporter.py
- logger.py
- requirements.txt
- packages.txt

## Deploy

No Streamlit Community Cloud:

Main file path:
`app.py`

## Fluxo de uso

1. Opcionalmente importe uma ou mais bases JSON.
2. Marque "Ignorar empresas já existentes".
3. Informe nicho, cidade, UF e quantidade.
4. Execute a pesquisa.
5. Exporte o JSON da pesquisa.
6. Exporte o JSON consolidado quando quiser atualizar sua base.

A aplicação não resolve CAPTCHA, não faz login e não tenta contornar mecanismos de segurança.
