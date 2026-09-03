# Hospedando o dashboard no Streamlit Community Cloud

Isso deixa o "Meu Portfólio B3" acessível de qualquer navegador, em
qualquer lugar, sem precisar do seu PC ligado — de graça, usando o mesmo
repositório privado que você já publicou no GitHub.

## Antes de começar

Essa parte só funciona depois de:

1. O código já estar publicado no GitHub (feito — repositório
   `PortfolioApp`, privado).
2. O Firestore já estar configurado como fonte de verdade (feito).

O dashboard hospedado vai rodar num computador do Streamlit, não no seu —
por isso ele não enxerga a pasta `~/.portfolio_b3_secrets` do seu PC, onde
ficam a chave do Firebase e a configuração de e-mail. Esses dois arquivos
precisam ser colados manualmente no site do Streamlit Cloud, num lugar
protegido chamado **"Secrets"** — nunca no código, nunca no GitHub.

## Passo 1: gerar o texto para colar nos "Secrets"

1. Dê um duplo-clique em **"Gerar Secrets Streamlit.bat"** (na pasta do
   projeto).
2. Isso cria um arquivo `secrets_streamlit_gerado.txt` dentro da sua pasta
   pessoal `~/.portfolio_b3_secrets` (a mesma pasta protegida de sempre —
   nunca dentro da pasta do projeto).
3. Abra esse arquivo com o Bloco de Notas e deixe ele aberto — você vai
   copiar o conteúdo dele daqui a pouco.

Se você ainda não configurou o celular (chave do Firebase) ou o e-mail de
alerta, o arquivo gerado vai avisar isso nos comentários — sem problema,
você pode hospedar o dashboard mesmo assim, só que ele não vai sincronizar
com a nuvem/e-mail até você configurar essas partes depois (e rodar este
gerador de novo).

## Passo 2: criar o app no Streamlit Community Cloud

1. Acesse [share.streamlit.io](https://share.streamlit.io) e entre com sua
   conta do GitHub (a mesma que você já usa no GitHub Desktop).
2. Se for a primeira vez, autorize o Streamlit a acessar seus
   repositórios — quando pedir, dê acesso também a **repositórios
   privados** (senão ele não vai enxergar o `PortfolioApp`).
3. Clique em **"Create app"** (ou "New app").
4. Escolha:
   - Repository: `SEU-USUARIO/PortfolioApp`
   - Branch: `main`
   - Main file path: `app.py`
5. Antes de clicar em "Deploy", clique em **"Advanced settings"**.
6. No campo **"Secrets"**, cole todo o conteúdo do arquivo
   `secrets_streamlit_gerado.txt` (Ctrl+A, Ctrl+C nele, depois Ctrl+V
   aqui).
7. Clique em **"Save"** e depois em **"Deploy"**.

A primeira publicação demora alguns minutos (o Streamlit instala as
bibliotecas do `requirements.txt` do zero). Quando terminar, você recebe
um link (algo como `https://SEU-APP.streamlit.app`) — esse é o endereço do
seu dashboard, acessível de qualquer navegador.

### Segurança antes da publicação

Publique as regras versionadas do Firestore antes de usar o app mobile:
`firebase deploy --only firestore:rules`, executado na raiz do projeto. O
arquivo `firebase.json` aponta para `firestore.rules`. As regras exigem login
para leitura e impedem alterações diretas na carteira pelo cliente mobile.

No app real, mantenha a seção `[login_site]` nos Secrets do Streamlit. Quando
ela existe, o dashboard interrompe a execução se a biblioteca ou as
credenciais estiverem ausentes, em vez de abrir sem proteção. O app demo deve
receber somente `[modo] demo = true`, sem Secrets da carteira.

## Passo 3 (opcional): um segundo link seguro para compartilhar com amigos

**Novidade (2026-08-30).** O link do Passo 2 mostra sua carteira REAL — não
mande esse link pra ninguém. Se você quiser mostrar o app pra um amigo (ou
qualquer outra pessoa) sem nenhum risco de expor seus dados, publique um
SEGUNDO app, à parte, no "modo demonstração": ele mostra uma carteira
inventada (tickers reais da B3, mas quantidades e valores fictícios) e
nunca lê nem grava nada da sua carteira de verdade — nem o arquivo local,
nem o Firestore. Mesmo que essa carteira de mentira seja "zerada" ou
bagunçada por quem estiver mexendo, ela sempre volta igual da próxima vez
que a página recarregar.

1. Repita o Passo 2 (Create app / New app), com **o mesmo repositório e
   branch** (`SEU-USUARIO/PortfolioApp`, `main`) — mas desta vez, em
   **"Main file path"**, coloque **`app_demo.py`** (não `app.py`). O
   Streamlit Cloud não deixa criar um segundo app com o mesmo arquivo
   principal do primeiro, mesmo com Secrets diferentes — `app_demo.py` é
   só uma "porta de entrada" separada que roda exatamente o mesmo app.py
   por trás (ver o próprio arquivo pra entender).
2. Em **"Advanced settings" → "Secrets"** deste segundo app, cole **só**
   isto (nada de chave do Firebase nem e-mail aqui — de propósito, pra
   esse link nunca ter acesso a nada real):
   ```toml
   [modo]
   demo = true
   ```
3. Clique em **"Deploy"**.

Pronto — esse segundo link (`https://SEU-APP-DEMO.streamlit.app`, um
endereço diferente do primeiro) mostra sempre a mesma carteira fictícia,
com um aviso "🎭 Modo demonstração" no topo da tela, e pode ser mandado
pra qualquer pessoa sem risco nenhum. Se um dia quiser tirar esse link do
ar, é só apagar esse segundo app em `share.streamlit.io -> Manage app ->
Delete app` — o link principal (com seus dados reais) não é afetado.

## Coisas para saber

- **O app "dorme" depois de 12h sem visitas.** Da próxima vez que alguém
  abrir o link, aparece uma tela de "acordar" e demora uns 10-30 segundos
  na primeira consulta. Normal, sem custo — é como o plano gratuito
  funciona.
- **Se você trocar a chave do Firebase ou o e-mail depois**, rode "Gerar
  Secrets Streamlit.bat" de novo e cole o novo texto em
  `share.streamlit.io -> seu app -> Settings -> Secrets`.
- **O risco das cotações via Yahoo Finance (yfinance) fora do seu PC** —
  explicado em `ESTUDO_ARQUITETURA_NUVEM.md` — continua valendo aqui: é
  possível que, hospedado, o app tome erro "429" ao buscar cotação de vez
  em quando. Se isso acontecer com frequência, me avisa que vemos as
  alternativas descritas naquele estudo.
- **O arquivo `secrets_streamlit_gerado.txt`** fica na sua pasta pessoal
  protegida, fora do projeto — pode apagá-lo depois de colar no site, já
  que ele nunca é lido pelo próprio app (só serve pra você copiar o
  conteúdo uma vez).
