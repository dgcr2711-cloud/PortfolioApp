# Alertas de preço em segundo plano (GitHub Actions + WhatsApp)

Até agora, o alerta de preço-alvo só era verificado quando **alguém
clicava em "🔄 Atualizar Dados"** — no seu PC ou num dos dashboards
hospedados. Se ninguém abrisse o app num dia em que uma ação caiu até o
preço-alvo, você só ficaria sabendo quando abrisse o app de novo.

Esta parte resolve isso: um robozinho roda sozinho, de hora em hora
(durante o horário do pregão da B3, de segunda a sexta), busca as
cotações e manda uma mensagem no seu **WhatsApp** na hora — mesmo com o
PC desligado e sem ninguém olhando o dashboard. Ele roda numa máquina do
GitHub (de graça), não no seu computador.

## Antes de começar

Isso só funciona depois de:

1. O repositório já estar publicado no GitHub (feito).
2. O celular/Firestore já estar configurado — isto é, você já tem o
   arquivo `firebase-service-account.json` em `~/.portfolio_b3_secrets`
   (ver README_MOBILE.md).

## Por que WhatsApp em vez de e-mail?

O projeto tinha originalmente um alerta por e-mail (ver
`core/notificacoes_email.py` — o código continua no projeto, só não é mais
usado), mas configurar exigia ativar a "Verificação em duas etapas" no
Google e gerar uma "senha de app". O WhatsApp é bem mais rápido: você só
manda uma mensagem para um número e recebe uma chave na hora.

**Um detalhe importante para saber**: isso funciona através de um serviço
gratuito de terceiros chamado **CallMeBot** (não é do WhatsApp/Meta) — ele
é confiável na maior parte do tempo, mas por ser gratuito e informal, pode
ocasionalmente ficar fora do ar por um tempo. Se um dia os alertas
pararem de chegar do nada, vale suspeitar disso antes de qualquer outra
coisa (o alerta na tela do app, ao abrir "Atualizar Dados", sempre
continua funcionando normalmente, independente disso).

## Passo 1: ativar o CallMeBot no seu WhatsApp

1. No seu celular, salve este número nos contatos, com qualquer nome
   (ex: "Robô Alertas"): **+34 694 23 41 84**
2. Abra o WhatsApp e mande para esse contato, exatamente, esta mensagem
   (copie e cole, sem mudar nada):

   ```
   I allow callmebot to send me messages
   ```

3. Em até 2 minutos, ele responde com uma mensagem parecida com:

   ```
   API Activated for your phone number. Your APIKEY is 123456
   ```

   Guarde esse número (a "apikey") — é a sua chave pessoal.

   Se não chegar nada em 2 minutos, espere 24h e tente de novo (limitação
   do próprio serviço gratuito).

## Passo 2: criar os 3 Secrets no GitHub

1. Abra `~/.portfolio_b3_secrets` no seu PC (cole
   `%USERPROFILE%\.portfolio_b3_secrets` na barra de endereço do
   Explorador de Arquivos) e deixe aberto, no Bloco de Notas, o arquivo
   `firebase-service-account.json`.
2. Acesse
   [https://github.com/dgcr2711-cloud/PortfolioApp/settings/secrets/actions](https://github.com/dgcr2711-cloud/PortfolioApp/settings/secrets/actions)
   (entre com sua conta do GitHub, se pedir).
3. Clique em **"New repository secret"** 3 vezes, uma para cada um destes:

   | Name (nome do Secret) | Secret (valor a colar) |
   |---|---|
   | `FIREBASE_SERVICE_ACCOUNT_JSON` | todo o conteúdo do arquivo `firebase-service-account.json` |
   | `WHATSAPP_ALERTA_NUMERO` | o seu número de WhatsApp, com código do país (ex: `+5511999999999`) |
   | `WHATSAPP_ALERTA_APIKEY` | a apikey que o CallMeBot te mandou no Passo 1 |

Ao final, a tela deve mostrar 3 Secrets cadastrados. Você não consegue
mais ver o conteúdo deles depois de salvos (só apagar e recadastrar, se
precisar trocar algum) — isso é proposital, é assim que o GitHub protege
esse cofre.

## Passo 3: testar uma vez, na mão

Não precisa esperar até a próxima hora cheia para saber se funcionou:

1. Acesse
   [https://github.com/dgcr2711-cloud/PortfolioApp/actions/workflows/verificar_alertas.yml](https://github.com/dgcr2711-cloud/PortfolioApp/actions/workflows/verificar_alertas.yml)
2. Clique no botão **"Run workflow"** (do lado direito), depois no botão
   verde **"Run workflow"** que aparece.
3. Espere uns 10-20 segundos e atualize a página — vai aparecer uma
   execução nova na lista, com uma bolinha amarela (rodando), depois
   verde (deu certo) ou vermelha (deu erro).
4. Clique nela para ver os detalhes — dentro de "Rodar a verificação de
   alertas" aparece uma mensagem tipo `[alertas] Verificação concluída. 0
   mensagem(ns) de WhatsApp enviada(s).` (0 é o normal, se nenhum dos seus
   alertas configurados tiver sido atingido agora).

Se a bolinha ficar vermelha, me manda um print da tela de detalhes que eu
te ajudo a diagnosticar.

## Coisas para saber

- **Horário**: roda de hora em hora, das 10h às 18h (horário de
  Brasília), de segunda a sexta — cobrindo o pregão da B3.
- **Custo**: zero. O GitHub Actions é de graça para repositórios
  públicos; o CallMeBot também é gratuito (só para uso pessoal, que é
  exatamente o seu caso).
- **Isso substitui o alerta de "Atualizar Dados"?** Não — os dois
  continuam funcionando (e ambos já usam WhatsApp agora), um não
  interfere no outro. Este aqui só cobre os horários em que ninguém abriu
  o app manualmente.
- **Onde ver o histórico de execuções**:
  [https://github.com/dgcr2711-cloud/PortfolioApp/actions/workflows/verificar_alertas.yml](https://github.com/dgcr2711-cloud/PortfolioApp/actions/workflows/verificar_alertas.yml)
- **Se um dia quiser trocar de número ou a apikey parar de funcionar**:
  refaça o Passo 1 (a mensagem de ativação pode ser mandada de novo a
  qualquer momento) e depois apague e recadastre o Secret
  `WHATSAPP_ALERTA_APIKEY` em
  [https://github.com/dgcr2711-cloud/PortfolioApp/settings/secrets/actions](https://github.com/dgcr2711-cloud/PortfolioApp/settings/secrets/actions)
- **Nunca cole o conteúdo desses arquivos nem a sua apikey aqui no chat
  comigo** — os Secrets do GitHub são o único lugar onde essas
  informações devem ir a partir de agora.
