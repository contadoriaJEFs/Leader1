# Leader1 V4 — Gerador de Leads Locais

## V4

Esta versão separa claramente:

1. **Coleta dos resultados**
2. **Enriquecimento dos resultados**

A busca tenta carregar progressivamente o feed do Google Maps até atingir a quantidade solicitada.

### Campos

- nome
- cidade
- estado
- endereco
- telefone
- horario_funcionamento
- whatsapp
- website
- instagram

### Correções

- Rolagem mais persistente do painel de resultados.
- Até 100 resultados solicitáveis.
- Contagem separada de solicitados e coletados.
- Horário de funcionamento separado do telefone.
- Proteção contra falsos telefones causados por horários.
- Enriquecimento executado somente depois da coleta.
- JSON e CSV.

## Streamlit

Main file path:

`app.py`

Teste recomendado:

`Academias / Recife / PE / 15`

A aplicação não resolve CAPTCHA, não faz login e não tenta contornar mecanismos de segurança.
