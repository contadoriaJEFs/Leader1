# Lead Scraper Local — Streamlit

Aplicação experimental para pesquisa pública de empresas locais, com exportação JSON/CSV e enriquecimento básico do website.

## Deploy no Streamlit Community Cloud

1. Crie um repositório público ou privado no GitHub.
2. Envie todos os arquivos deste projeto.
3. No Streamlit Community Cloud, selecione o repositório e o arquivo `app.py`.
4. Faça o deploy.
5. O endereço da aplicação será fornecido pelo Streamlit.

## Observação sobre Playwright

O aplicativo usa Playwright para abrir a pesquisa do Google Maps. O navegador Chromium precisa estar disponível no ambiente de execução.

Se o ambiente de deploy não instalar o navegador automaticamente, será necessário ajustar a configuração de build do Streamlit/ambiente. O código não tenta resolver CAPTCHAs, fazer login ou contornar bloqueios.

## Uso

Informe:
- Nicho
- Cidade
- UF
- Quantidade

Clique em **Iniciar busca**.

Depois, exporte JSON ou CSV.

## Estrutura do JSON

Cada lead possui:

- nome
- cidade
- estado
- endereco
- telefone
- whatsapp
- website
- instagram

Campos não encontrados ficam como `null`.

## Limitações

O DOM do Google Maps pode mudar. A coleta deve ser considerada um protótipo e pode exigir manutenção dos seletores.

Respeite as regras e termos aplicáveis aos sites consultados e não tente contornar mecanismos de segurança.
