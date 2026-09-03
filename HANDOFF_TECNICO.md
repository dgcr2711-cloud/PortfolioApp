# Handoff Técnico — Meu Portfólio B3

> **Nota importante antes de tudo**: seu pedido mencionou Supabase, React/TypeScript, rotas e políticas RLS — mas **nada disso existe neste projeto**. Conferi o código inteiro (`grep` em todos os arquivos `.py`, `.ts`, `.tsx`, `.md`) e a única menção a "Supabase" no projeto todo é uma linha no arquivo `ESTUDO_ARQUITETURA_NUVEM.md` descrevendo Postgres/Supabase como uma **alternativa que foi avaliada e rejeitada** (exigiria reescrever tudo, sem ganho real pro seu caso). O que realmente construímos juntos é **Python + Streamlit** (site) **+ Firebase/Firestore** (banco de dados na nuvem) **+ React Native/Expo** (app do celular, esse sim em TypeScript). Se você pediu esse resumo pensando em OUTRO projeto seu, me avise que eu ajusto. Se era este projeto mesmo, segue abaixo o resumo certo, na mesma estrutura que você pediu.

---

## 1. O que já foi feito (código realizado)

**Site (dashboard na nuvem, hospedado em [meuportfolio.streamlit.app](https://meuportfolio.streamlit.app))** — Python + [Streamlit](https://streamlit.io), sem front-end separado (o próprio Streamlit desenha a tela a partir do Python).

- `app.py` — ponto de entrada. Monta a barra lateral, controla qual aba está ativa (`st.session_state["aba_ativa"]` — é o equivalente deste projeto a "rotas": não são URLs, são 10 telas trocadas por botão dentro da mesma página) e chama o login antes de mostrar qualquer dado.
- `core/` (24 módulos) — toda a lógica que não depende do Streamlit, testável isoladamente: `calculations.py` (preço médio, TWR), `cloud_sync.py` (sincronização com Firestore), `data_store.py` (carregar/salvar dados, local + nuvem), `auth.py` (login do site), `market_data.py`, `fundamentals.py`, `piotroski.py`, `altman.py`, `valuation_multiplos.py`, `imposto_renda.py`, `risco.py`, `rebalanceamento.py`, `notificacoes_email.py`, `notificacoes_whatsapp.py`, entre outros.
- `ui/` (13 módulos) — uma tela por aba: `visao_geral.py`, `carteira.py`, `compras.py`, `proventos.py`, `preco_teto.py`, `fundamentos.py`, `evolucao.py`, `imposto_renda.py`, `tese_investimento.py`, `configuracoes.py`, mais `styles.py` (CSS injetado — ajustado agora há pouco pra deixar tudo mais compacto e organizado).
- `tests/` — 345 testes automatizados cobrindo os cálculos e o carregamento de dados.

**App do celular (`mobile-app/`)** — React Native + Expo + **TypeScript** (essa parte sim é a que mais se parece com o que você descreveu): `App.tsx`, `src/firebase.ts` (configuração do cliente Firebase — equivalente ao "supabaseClient" que você mencionou, mas apontando pro Firebase), `src/screens/`, `src/components/`, `src/contexts/`, `src/hooks/`.

**Configuração do "cliente" de nuvem** (equivalente ao que seria o `supabaseClient`), em `core/cloud_sync.py`:
- Inicializa o Firebase Admin SDK a partir da chave de serviço em `~/.portfolio_b3_secrets/firebase-service-account.json` (fora da pasta do projeto, de propósito, pra nunca ir parar no GitHub).
- Toda chamada ao Firestore tem timeout configurado (`TIMEOUT_FIRESTORE_SEGUNDOS = 10`, mais um limite total de 12s usando uma thread separada) — corrigido recentemente porque uma chamada sem limite estava travando a tela toda em branco.

---

## 2. Estrutura do banco de dados (Firebase Firestore, não Supabase)

Não existem "tabelas" nem RLS (isso é terminologia de banco relacional/Postgres). O Firestore é um banco de documentos, organizado em **coleções**:

| Coleção | Documento | Conteúdo |
|---|---|---|
| `portfolio` | `snapshot` | Snapshot resumido da carteira |
| `portfolio` | `dados_completos` | Todos os dados: compras, cotações, proventos, histórico, alertas, setores, preços-teto, watchlist, releases, análises, indicadores |
| `pendencias_compras` | (vários, com `status`) | Compras/vendas lançadas pelo app do celular, aguardando confirmação |
| `pendencias_remocoes` | (vários) | Remoções pendentes |
| `pendencias_preco_teto` | (vários) | Alterações de preço-teto pendentes |
| `pendencias_teses` | (vários) | Alterações no diário de teses pendentes |

Segurança: não usamos regras de segurança do Firestore (RLS) porque o acesso é feito só pelo backend com a chave de serviço (Admin SDK), não direto do navegador/celular do usuário final — é você mesmo, sozinho, usando o app. A proteção do site hospedado é feita por login próprio (usuário/senha via `streamlit-authenticator`), configurado em `[login_site]` nos Secrets do Streamlit Cloud.

---

## 3. O que ainda não foi feito (pendências)

- Integração com a API HG Brasil — ainda não testada/decidida.
- Página de "lâminas" de estudo — você mesmo pediu para deixar para depois ("mais para frente, não agora").
- Build standalone do app do celular para iOS (custo de ~US$99/ano na Apple) — decisão pendente sua.
- Esclarecer o que você quis dizer com "cálculos completos com JS" — ainda não entendido/definido.
- Dar retorno sobre o wireframe/protótipo de UX publicado anteriormente.
- Confirmar se a correção mais recente (timeout na busca do Firestore) resolveu de vez a tela em branco no app local — ainda aguardando você testar e confirmar.

---

*Gerado automaticamente a partir do código real do projeto em 2026-09-03.*
