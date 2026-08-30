# Meu Portfólio B3 — App Streamlit

Versão do seu dashboard de investimentos rodando como aplicativo local em
Python, com Streamlit. Mantém os mesmos cards de resumo, tabelas e
gráficos do dashboard em HTML, mas agora busca as cotações automaticamente
no Yahoo Finance (via `yfinance`) em vez de depender do navegador.

## O que tem nesta primeira versão

- **🏠 Visão Geral** — os 5 cards de resumo + tabela compacta com todos os
  ativos (carteira + empresas-alvo).
- **📈 Carteira** — cards de patrimônio/resultado, tabela detalhada de
  posições (Preço Médio, Preço Teto, Margem de Segurança, Indicação
  Compra/Neutro/Venda, Alerta) e o gráfico de alocação por ativo ou setor.
- **🧾 Compras & Vendas** — lançar compras, vendas e eventos societários
  (desdobramento/grupamento/bonificação), preço médio ponderado, resultado
  realizado das vendas e o resumo mensal simplificado de IR.
- **📅 Proventos** — registro de dividendos/JCP/rendimentos e Yield on Cost.
- **🎯 Preço Teto** — calculadora de Fluxo de Caixa Descontado (2 estágios),
  igual à do dashboard original.
- **📊 Evolução** — gráfico de patrimônio ao longo do tempo + comparativo
  com o Ibovespa (TWR aproximado).
- **⚙️ Configurações** — alertas de preço, lista de observação e
  backup (exportar/importar `.json`).
- Botão **🔄 Atualizar Dados** na barra lateral (visível em qualquer aba):
  força uma busca nova de preços no Yahoo Finance.

**O que ficou de fora desta primeira versão** (para manter o escopo
gerenciável — dá pra adicionarmos nas próximas iterações): a leitura
automática de PDFs de release para preencher o FCD, e a aba de
Indicadores Fundamentalistas (P/L, P/VP, ROE etc.). Os links diretos de RI
continuam disponíveis na aba Preço Teto para consulta manual.

**Sobre o visual:** o app usa componentes nativos do Streamlit (cards,
tabelas, gráficos Plotly) com o mesmo tema escuro e as mesmas cores do
dashboard original (fundo cinza-escuro, destaque verde-esmeralda), e
reproduz a mesma estrutura de seções, colunas e badges (🟢 Compra / 🟡
Neutro / 🔴 Venda). Não é uma cópia pixel-a-pixel do HTML/Tailwind — o
Streamlit gera sua própria interface — mas a organização da informação é
a mesma.

## Passo a passo para rodar no seu computador (Windows)

### 1. Instalar o Python (se ainda não tiver)

Baixe em https://www.python.org/downloads/ (marque a opção **"Add
python.exe to PATH"** durante a instalação). Para conferir se já está
instalado, abra o **Prompt de Comando** e rode:

```
python --version
```

### 2. Abrir o Prompt de Comando na pasta do app

Copie a pasta `PortfolioApp` (esta pasta) para onde preferir — por
exemplo, dentro de `Carteira de investimentos` na área de trabalho, onde
já está. Depois, no Explorador de Arquivos, entre na pasta `PortfolioApp`,
clique na barra de endereço, digite `cmd` e aperte Enter — isso abre o
Prompt de Comando já na pasta certa.

### 3. Criar um ambiente virtual (recomendado)

Isola as bibliotecas deste projeto do resto do seu Python:

```
python -m venv venv
venv\Scripts\activate
```

Você saberá que funcionou porque o início da linha do terminal passa a
mostrar `(venv)`. **Repita esse `venv\Scripts\activate` toda vez que for
abrir o app num novo Prompt de Comando.**

### 4. Instalar as bibliotecas necessárias

```
pip install -r requirements.txt
```

Isso instala `streamlit`, `yfinance`, `pandas` e `plotly`. Só precisa
rodar de novo se o arquivo `requirements.txt` mudar no futuro.

### 5. Rodar o app

```
streamlit run app.py
```

O terminal vai mostrar um endereço como `http://localhost:8501` e o
navegador deve abrir automaticamente nessa página. Se não abrir sozinho,
copie esse endereço e cole no navegador.

Para **parar** o app, volte ao terminal e aperte `Ctrl+C`.

### 6. Trazer seus dados reais para o app

Os dados começam vazios (só com a lista de observação padrão). Para trazer
sua carteira real:

1. Abra o dashboard antigo (`dashboard-investimentos-b3.html`, na pasta
   Downloads) no navegador.
2. Vá em **⚙️ Configurações → 💾 Backup dos Dados → ⬇️ Exportar dados
   (.json)** e salve o arquivo.
3. No app novo, vá em **⚙️ Configurações → 💾 Backup dos Dados → ⬆️
   Importar dados (.json)** e selecione esse arquivo.

Isso importa compras, vendas, proventos, preços-teto, alertas, setores,
watchlist e o histórico de patrimônio — exatamente os mesmos dados que
você já tinha. Um backup automático dos dados atuais do app é salvo em
`data/backups/` antes de qualquer importação, então nada se perde.

> 💡 Prefira sempre exportar o backup mais recente do dashboard antigo
> antes de importar — assim você garante que está trazendo a versão mais
> atualizada da sua carteira.

### 7. (Opcional) Receber um e-mail quando um alerta de preço for atingido

**Novidade (2026-08-30).** Além do selo 🔔/🔕 na coluna Alerta, o app pode
mandar um e-mail pra você assim que a cotação de um ativo cair até (ou
abaixo d)o preço configurado em **⚙️ Configurações → 🔔 Alertas de
Preço-Alvo**. Pesquisei notificação push de verdade no celular antes de
implementar isso, e ela exigiria o mesmo custo do login do Google (US$99/ano
no Programa de Desenvolvedor Apple — ver README_MOBILE.md) num iPhone;
e-mail chega no celular na hora (a maioria já notifica e-mail novo) sem
nenhum custo, então foi o caminho escolhido.

Essa etapa é 100% opcional — sem configurar nada, o app continua funcionando
normalmente, só sem o e-mail. **Eu não crio essa conta nem vejo sua senha**:
você mesmo cria um arquivo de configuração com um editor de texto, seguindo
os passos abaixo.

1. No Gmail que você quer usar para enviar o alerta, ative a "Verificação em
   duas etapas" (se ainda não tiver): [myaccount.google.com/security](https://myaccount.google.com/security).
   O Gmail exige isso antes de liberar uma "senha de app" — é o passo
   seguinte.
2. Ainda em [myaccount.google.com/security](https://myaccount.google.com/security),
   procure "Senhas de app" (App Passwords), crie uma nova (pode chamar de
   "Meu Portfólio B3") e copie a senha de 16 letras que aparece. **Essa não é
   a sua senha normal do Gmail** — é uma senha específica só para este uso,
   que você pode revogar a qualquer momento sem afetar sua conta.
3. Abra o Bloco de Notas do Windows e cole o texto abaixo, trocando pelos
   seus dados (o `destinatario` pode ser o mesmo e-mail do `remetente`, se
   quiser receber no mesmo Gmail que envia):
   ```json
   {
       "remetente": "seuemail@gmail.com",
       "senha_app": "a senha de 16 letras do passo 2, com ou sem espaços",
       "destinatario": "seuemail@gmail.com"
   }
   ```
4. Salve esse arquivo como `email_alertas.json` (no Bloco de Notas, escolha
   "Salvar como", tipo "Todos os arquivos", e cole o caminho completo abaixo
   no campo de nome do arquivo — troque `SeuUsuario` pelo nome de usuário do
   seu Windows):
   ```
   C:\Users\SeuUsuario\.portfolio_b3_secrets\email_alertas.json
   ```
   Essa é a mesma pasta oculta (fora da pasta do projeto) onde já fica a
   chave do Firebase, se você configurou o celular — se a pasta não
   existir ainda, crie-a antes (no Explorador de Arquivos, cole
   `C:\Users\SeuUsuario\.portfolio_b3_secrets` na barra de endereço e
   confirme criar a pasta).
5. Feche e abra o app de novo (janela preta do "Iniciar App.bat") pra ele
   ler o arquivo novo. Na próxima vez que clicar em "🔄 Atualizar Dados" (ou
   "🔄 Atualizar Cotações") com algum alerta atingido, o e-mail é enviado.

Cada alerta manda só UM e-mail por queda — se o preço voltar a subir acima
do seu alvo e cair de novo depois, um novo e-mail é enviado nessa próxima
queda (não fica repetindo o mesmo e-mail a cada "Atualizar Dados" enquanto
o preço não se mexe).

## Estrutura do projeto

```
PortfolioApp/
├── app.py                 # ponto de entrada (streamlit run app.py)
├── requirements.txt       # bibliotecas necessárias
├── .streamlit/config.toml # tema escuro do app
├── core/                  # regras de negócio (sem depender do Streamlit)
│   ├── config.py          # constantes (margem de segurança, limite de IR etc.)
│   ├── data_store.py      # carregar/salvar/exportar/importar o JSON de dados
│   ├── calculations.py    # preço médio, preço teto, IR, TWR, FCD...
│   ├── market_data.py     # busca de cotações via yfinance (com cache)
│   ├── notificacoes_email.py  # e-mail de alerta de preço-alvo (opcional)
│   └── formatting.py      # formatação de R$ e % no padrão brasileiro
├── ui/                    # uma função de renderização por aba
│   ├── visao_geral.py, carteira.py, compras.py, proventos.py,
│   │   preco_teto.py, evolucao.py, configuracoes.py
│   ├── ativos.py          # monta a lista combinada de posições + alvo
│   ├── acoes_comuns.py    # atualização de cotações (botão "Atualizar Dados")
│   └── styles.py          # CSS dos cards/badges
└── data/
    └── portfolio_data.json  # seus dados (criado automaticamente)
```

Para adicionar uma funcionalidade nova numa próxima conversa, basta dizer
qual aba/comportamento você quer mudar — a estrutura modular faz com que
cada ajuste geralmente mexa em um único arquivo.
