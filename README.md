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

### 7. (Opcional) Receber uma mensagem de WhatsApp quando um alerta de preço for atingido

**Novidade (2026-08-30, canal trocado para WhatsApp em 2026-08-31).** Além
do selo 🔔/🔕 na coluna Alerta, o app pode mandar uma mensagem no seu
WhatsApp assim que a cotação de um ativo cair até (ou abaixo d)o preço
configurado em **⚙️ Configurações → 🔔 Alertas de Preço-Alvo**.

Essa etapa é 100% opcional — sem configurar nada, o app continua funcionando
normalmente, só sem a mensagem. Isso usa um serviço gratuito de terceiros
chamado **CallMeBot** (não é do WhatsApp/Meta) — **eu não crio essa conta
nem vejo nada seu**: você mesmo ativa em 2 minutos pelo próprio WhatsApp e
cria um arquivo de configuração com um editor de texto, seguindo os passos
abaixo.

1. No seu celular, salve este número nos contatos, com qualquer nome (ex:
   "Robô Alertas"): **+34 694 23 41 84**
2. Mande para esse contato, pelo WhatsApp, exatamente esta mensagem:
   ```
   I allow callmebot to send me messages
   ```
3. Em até 2 minutos ele responde com uma "apikey" (um número). Guarde-a —
   é a sua chave pessoal. (Se não chegar em 2 minutos, espere 24h e tente
   de novo.)
4. Abra o Bloco de Notas do Windows e cole o texto abaixo, trocando pelos
   seus dados (`numero` é o seu próprio WhatsApp, com código do país):
   ```json
   {
       "numero": "+5511999999999",
       "apikey": "a apikey que o CallMeBot te mandou no passo 3"
   }
   ```
5. Salve esse arquivo como `whatsapp_alertas.json` (no Bloco de Notas,
   escolha "Salvar como", tipo "Todos os arquivos", e cole o caminho
   completo abaixo no campo de nome do arquivo — troque `SeuUsuario` pelo
   nome de usuário do seu Windows):
   ```
   C:\Users\SeuUsuario\.portfolio_b3_secrets\whatsapp_alertas.json
   ```
   Essa é a mesma pasta oculta (fora da pasta do projeto) onde já fica a
   chave do Firebase, se você configurou o celular — se a pasta não
   existir ainda, crie-a antes (no Explorador de Arquivos, cole
   `C:\Users\SeuUsuario\.portfolio_b3_secrets` na barra de endereço e
   confirme criar a pasta).
6. Feche e abra o app de novo (janela preta do "Iniciar App.bat") pra ele
   ler o arquivo novo. Na próxima vez que clicar em "🔄 Atualizar Dados" (ou
   "🔄 Atualizar Cotações") com algum alerta atingido, a mensagem é enviada.

Cada alerta manda só UMA mensagem por queda — se o preço voltar a subir
acima do seu alvo e cair de novo depois, uma nova mensagem é enviada nessa
próxima queda (não fica repetindo a mesma mensagem a cada "Atualizar
Dados" enquanto o preço não se mexe). Por ser um serviço gratuito e
informal, o CallMeBot pode ocasionalmente ficar fora do ar — se os
alertas pararem de chegar do nada, vale suspeitar disso primeiro (o app
em si continua funcionando normalmente).

> O projeto também tem um alerta por e-mail (`core/notificacoes_email.py`),
> da versão anterior a esta mudança — o código continua no projeto, só não
> está mais em uso.

### 8. (Opcional) Taxas SELIC/CDI e cotações de reforço via HG Brasil Finance

**Novidade (2026-09-03).** O app pode mostrar a SELIC e o CDI mais
recentes na aba Visão Geral, e usar a API da HG Brasil como plano B para
cotações de ações/FIIs quando o Yahoo Finance falhar para algum ticker —
ver `core/market_data.py`. Essa etapa é 100% opcional: sem configurar, o
app continua funcionando exatamente como hoje, só sem essas duas coisas.

1. Se ainda não tiver, crie uma conta em
   [console.hgbrasil.com](https://console.hgbrasil.com/) e copie a chave
   (token) da API "Finance".
2. Dê um duplo-clique em **"Configurar Chave HG Brasil.bat"** e cole a
   chave quando pedido. Ela fica salva em
   `C:\Users\SeuUsuario\.portfolio_b3_secrets\hgbrasil_api_key.json` — a
   mesma pasta oculta, fora do projeto, onde já ficam as outras chaves.
3. Se você também hospeda o dashboard na nuvem (próximo passo abaixo), rode
   "Gerar Secrets Streamlit.bat" de novo e cole o resultado atualizado nos
   Secrets do site.

Nota sobre o plano da sua conta HG Brasil: o endpoint de cotação
individual (usado só como plano B, quando o Yahoo Finance falha) exige um
plano pago acima do gratuito — se a sua conta for gratuita, o app
simplesmente ignora esse reforço (sem erro nenhum) e continua contando
100% com o Yahoo Finance para preços, como sempre. As taxas SELIC/CDI, por
outro lado, funcionam com qualquer chave, inclusive gratuita.

### 9. (Opcional) Hospedar o dashboard na nuvem, acessível de qualquer lugar

**Novidade (2026-08-30).** Além de rodar no seu PC, o dashboard pode ficar
hospedado de graça no Streamlit Community Cloud, com um link acessível de
qualquer navegador (celular incluso), sem precisar do seu PC ligado. Veja
o passo a passo completo em `README_HOSPEDAGEM.md`.

### 10. (Opcional) Verificar alertas de preço em segundo plano, mesmo com o PC desligado

**Novidade (2026-08-31).** Além do alerta que dispara quando você clica em
"🔄 Atualizar Dados", um robô pode rodar sozinho de hora em hora (durante o
pregão da B3), de graça, pelo GitHub Actions — útil pra quando ninguém abre
o app num dia em que um alerta seria atingido. Veja o passo a passo
completo em `README_ALERTAS_SEGUNDO_PLANO.md`.

## Estrutura do projeto

```
PortfolioApp/
├── app.py                 # ponto de entrada (streamlit run app.py)
├── requirements.txt       # bibliotecas necessárias
├── .streamlit/config.toml # tema escuro do app
├── core/                  # regras de negócio (sem depender do Streamlit)
│   ├── config.py          # constantes (margem de segurança, limite de IR etc.)
│   ├── data_store.py      # carregar/salvar/exportar/importar os dados (local + Firestore)
│   ├── cloud_sync.py      # sincronização com o Firestore (celular + dashboard hospedado)
│   ├── calculations.py    # preço médio, preço teto, IR, TWR, FCD...
│   ├── market_data.py     # busca de cotações via yfinance (com cache) + SELIC/CDI e reforço via HG Brasil
│   ├── notificacoes_whatsapp.py  # alerta de preço-alvo por WhatsApp (opcional)
│   ├── notificacoes_email.py  # alerta por e-mail (versão anterior, sem uso ativo)
│   └── formatting.py      # formatação de R$ e % no padrão brasileiro
├── ui/                    # uma função de renderização por aba
│   ├── visao_geral.py, carteira.py, compras.py, proventos.py,
│   │   preco_teto.py, evolucao.py, configuracoes.py
│   ├── ativos.py          # monta a lista combinada de posições + alvo
│   ├── acoes_comuns.py    # atualização de cotações (botão "Atualizar Dados")
│   └── styles.py          # CSS dos cards/badges
├── scripts/
│   └── verificar_alertas_segundo_plano.py  # roda no GitHub Actions (ver README_ALERTAS_SEGUNDO_PLANO.md)
├── .github/workflows/
│   └── verificar_alertas.yml  # agendamento do robô de alertas (hora em hora, no pregão)
├── gerar_secrets_streamlit.py  # gera o texto de Secrets para hospedar no Streamlit Cloud (ver README_HOSPEDAGEM.md)
└── data/
    └── portfolio_data.json  # seus dados (criado automaticamente)
```

Para adicionar uma funcionalidade nova numa próxima conversa, basta dizer
qual aba/comportamento você quer mudar — a estrutura modular faz com que
cada ajuste geralmente mexa em um único arquivo.
