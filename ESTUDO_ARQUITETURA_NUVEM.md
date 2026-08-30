# Estudo: levar o Meu Portfólio B3 pra nuvem

Seu amigo programador trouxe 4 ideias. Separei cada uma, pesquisei as
ferramentas reais disponíveis hoje (2026) pra cada uma, e no fim junto tudo
numa recomendação. Achei também um problema técnico real que ninguém tinha
mencionado ainda — está na seção "⚠️ O ponto crítico" antes da recomendação
final, porque ele muda a resposta de quase tudo abaixo.

---

## 1. "Concatenar nossos dados e publicar na rede, tudo em nuvem"

**O que já existe hoje:** o PC já manda um retrato (snapshot) calculado pro
Firestore (nuvem do Google) toda vez que você clica em "Atualizar Dados" —
é assim que o celular lê sua carteira. Mas o **arquivo principal**
(`data/portfolio_data.json`, com todo o histórico de compras, vendas,
preços-teto etc.) mora só no seu PC. O Firestore hoje é uma "cópia
resumida só de leitura", não a fonte de verdade.

**O que seu amigo propõe:** inverter isso — o Firestore (ou outro banco na
nuvem) vira a fonte de verdade principal, e tanto PC quanto um dashboard
hospedado leem/escrevem direto lá. Dá pra fazer, usando o que você já tem:

| Ferramenta | Por quê |
|---|---|
| **Firestore** (já em uso) | Continuar com ele evita reescrever toda a lógica de sincronização que já existe e já funciona — só muda ele de "espelho" pra "fonte de verdade". |
| Alternativa: Postgres/Supabase | Mais "banco de dados de verdade" (consultas mais ricas), mas exigiria reescrever todo o `core/data_store.py` do zero — esforço grande sem ganho real pro seu caso (poucos dados, poucos usuários). |

**Recomendação:** manter o Firestore, só mudar o "sentido" da sincronização.
Isso é o alicerce de tudo que vem depois — sem isso, os itens 2 e 5 não
funcionam de verdade.

---

## 2. "O app poder rodar independente, de qualquer lugar"

Hoje o dashboard (Streamlit) só existe enquanto o app está aberto no SEU PC
(a janela preta). Rodar "de qualquer lugar" significa hospedar essa
mesma interface num servidor que fica sempre ligado, não no seu computador.

| Ferramenta | Custo | Esforço | Observação |
|---|---|---|---|
| **Streamlit Community Cloud** | Grátis | Baixo | Feito sob medida pra apps Streamlit. Mas: **precisa de um repositório no GitHub** (público ou privado — hoje seu projeto não tem nenhum), e **o app "dorme" depois de 12h sem visitas**, acordando de novo (com uma telinha de "clique para acordar") na próxima vez que alguém visitar. [Fonte](https://docs.streamlit.io/deploy/streamlit-community-cloud) |
| Render / Railway (free tier) | Grátis (com limites) ou ~US$5-7/mês | Médio | Mais flexível, mas também "dorme" nos planos grátis e exige mais configuração manual (Docker, variáveis de ambiente). |
| Google Cloud Run | Pague-conforme-uso (geralmente centavos/mês pro seu volume) | Médio-alto | Não dorme com a mesma agressividade, mas exige cartão cadastrado e mais conhecimento técnico pra configurar. |

**Recomendação:** Streamlit Community Cloud é o caminho mais barato e mais
simples — mas o app "dormir" depois de 12h parado é uma limitação real:
você (ou qualquer visitante) precisa clicar pra acordar, e a PRIMEIRA
consulta depois disso demora uns 10-30 segundos. Pra você, que é o único
usuário, isso é inconveniente mas não é um problema grave.

---

## 3. "Sem pagar a Apple"

Boa notícia: **hospedar o dashboard na nuvem não tem NADA a ver com a Apple.**
A taxa de US$99/ano (Programa de Desenvolvedor Apple) só existe pra colocar
um app NATIVO na App Store ou usar certos recursos nativos do iPhone (como
notificação push de verdade ou login do Google de verdade) — que é o tema
que discutimos antes sobre o app do celular. Um dashboard hospedado é só um
site: seu celular (iPhone ou Android) simplesmente abre ele pelo navegador.
Nenhuma das ferramentas do item 2 exige nada da Apple.

---

## 4. "Enviar alertas via WhatsApp"

| Ferramenta | Custo | Esforço | Risco |
|---|---|---|---|
| **CallMeBot** (não-oficial) | Grátis | Muito baixo — manda uma mensagem pro número do bot, recebe uma chave, e pronto | É um serviço de terceiros (não é do WhatsApp/Meta), então pode sair do ar ou mudar de regra sem aviso — mas é usado por muita gente há anos pra exatamente esse caso (mandar alerta pra você mesmo). [Fonte](https://www.callmebot.com/blog/free-api-whatsapp-messages/) |
| Meta WhatsApp Cloud API (oficial) | Primeiras conversas grátis, depois cobra por conversa | Alto — exige criar uma conta comercial (Meta Business), verificação, e aprovar modelos de mensagem | Baixo (é a via oficial), mas é MUITO mais burocrático pra mandar um alerta só pra você mesmo. |
| whatsapp-web.js / Baileys (auto-hospedado) | Grátis | Alto — precisa manter um servidor rodando 24h com seu WhatsApp "logado" nele | Contra os termos de uso do WhatsApp pra automação — risco real de SEU número pessoal ser banido. Não recomendo. |
| **Telegram Bot API (oficial)** — alternativa que já te sugeri antes | Grátis | Muito baixo, e é 100% oficial/documentado, sem risco de banimento | Só que é Telegram, não WhatsApp — exige você (ou eu te guiando) instalar o Telegram e criar um bot em 2 minutos. |

**Recomendação:** se o objetivo é "chegar uma mensage no celular, de graça,
sem risco pro seu WhatsApp pessoal", CallMeBot é a opção mais parecida com
o que seu amigo sugeriu, mas Telegram continua sendo a via mais robusta e
sem nenhum risco de conta banida. Dá pra fazer as duas, se quiser — é só
mais uma função no mesmo módulo de notificações que já criei pro e-mail.

---

## 5. "Trabalhar em segundo plano"

Hoje, o alerta só é checado quando VOCÊ clica em "Atualizar Dados" no PC —
ou seja, "segundo plano" de verdade (checar sozinho, mesmo com o PC
desligado) exige algo rodando na nuvem, sem depender de você clicar em nada.

| Ferramenta | Custo | Esforço | Observação |
|---|---|---|---|
| **GitHub Actions (cron agendado)** | Grátis (repo privado tem ~2.000 minutos grátis/mês — sobra muito pro seu caso) | Baixo-médio | Roda um script Python a cada X minutos, buscando cotações e mandando alerta, sem precisar do PC ligado. Não precisa cartão de crédito. Intervalo mínimo: 5 minutos. [Fonte](https://cronuru.com/guides/github-actions-scheduled-workflows) |
| Firebase Cloud Functions agendada | Geralmente US$0 na prática (dentro da cota grátis), mas... | Médio | ...**exige ativar o plano pago "Blaze" do Firebase** (cadastrar um cartão), mesmo que o uso real fique de graça — é só uma trava de segurança do Google, mas é um cartão cadastrado numa conta com cobrança "por uso". |

**Recomendação:** GitHub Actions é o caminho mais simples e sem exigir
cartão de crédito nenhum.

---

## ⚠️ O ponto crítico que descobri (afeta TUDO acima)

O app usa `yfinance` pra buscar as cotações — uma biblioteca que **não é
oficial do Yahoo Finance**, ela "lê" o site como se fosse um navegador.
Isso funciona bem do SEU PC (seu IP residencial de casa), mas o Yahoo
Finance é conhecido por **bloquear/limitar agressivamente pedidos vindos de
IPs de serviços de nuvem** (Streamlit Cloud, GitHub Actions, Render — todos
compartilham faixas de IP de datacenter com milhares de outros usuários).
Há relatos constantes na comunidade do Streamlit de apps que funcionam
perfeitos no PC do desenvolvedor e recebem erro "429 Too Many
Requests"/"Rate Limited" assim que são hospedados na nuvem. [Fonte 1](https://discuss.streamlit.io/t/asked-again-since-no-one-answered-http-429-error-only-when-hosted-it-is-fine-locally/38198) [Fonte 2](https://github.com/ranaroussi/yfinance/issues/2422)

**Na prática:** mover o app pra nuvem (itens 2 e 5) pode fazer as cotações
pararem de atualizar direito, de forma imprevisível — justo a parte mais
importante do app. Não é um "talvez nunca aconteça", é um problema muito
relatado.

**Como resolver, se quisermos seguir com a nuvem:**
1. Testar primeiro (é barato: só implementar o item 5 sozinho, sem mexer
   no resto, e ver se o GitHub Actions consegue buscar cotações de forma
   confiável por algumas semanas) — ou
2. Trocar o `yfinance` por uma API de verdade (paga) feita pra isso, tipo
   a [brapi.dev](https://brapi.dev) (especializada em ações da B3) — mas
   os planos pagos dela começam em uma mensalidade, deixando de ser "sem
   custo".

---

## Arquitetura recomendada, se você quiser seguir em frente

```
┌─────────────────┐        ┌──────────────────────┐
│   GitHub Actions │──────▶ │  Firestore (nuvem)    │◀──────┐
│  (roda a cada    │ grava  │  fonte de verdade      │ lê    │
│   X minutos,      │        │  única (compras,       │        │
│   busca cotação,  │        │  alertas, preço teto)  │        │
│   checa alertas)  │        └──────────────────────┘        │
└────────┬─────────┘                                          │
         │ manda e-mail/WhatsApp/Telegram                     │
         ▼                                                     │
   📧 📱 Você                                                   │
                                                                 │
┌──────────────────────┐                                       │
│ Streamlit Community   │───────────────────────────────────────┘
│ Cloud (dashboard,      │  lê/escreve
│ acessível de qualquer  │
│ lugar pelo navegador)  │
└──────────────────────┘
```

- Um script (rodando no GitHub Actions) cuida só de buscar cotação +
  checar alerta + notificar — o "segundo plano" de verdade.
- O dashboard (Streamlit Community Cloud) fica hospedado, acessível de
  qualquer navegador, sem depender do seu PC ligado.
- O PC deixa de ser obrigatório pro dia a dia — vira só mais um jeito de
  acessar a mesma coisa, se quiser.

**Esforço total estimado:** isso é uma reformulação grande — bem maior que
qualquer coisa que fizemos até agora neste projeto (que sempre foi
"adicionar uma função nova a um app que já funciona"). Envolve criar conta
no GitHub, aprender a exportar seus dados atuais pro Firestore sem perder
nada, testar a hospedagem, e validar que as cotações continuam confiáveis.
Não é impossível, mas não é uma tarde de trabalho.

## Minha recomendação de ordem

1. Primeiro, resolver só o item ⚠️ isoladamente: um teste pequeno rodando
   busca de cotação pelo GitHub Actions por 1-2 semanas, só pra confirmar
   se o Yahoo Finance bloqueia ou não no seu caso — sem mexer em mais nada.
2. Se passar no teste: migrar o Firestore pra fonte de verdade (item 1).
3. Depois: hospedar o dashboard (item 2) e ligar o alerta em segundo plano
   com WhatsApp/Telegram (itens 4 e 5) — a essa altura é só reaproveitar o
   `core/notificacoes_email.py` que já existe, adicionando as novas vias.

Isso evita gastar esforço grande em hospedagem antes de saber se a base
técnica (cotações confiáveis fora do seu PC) realmente aguenta.
