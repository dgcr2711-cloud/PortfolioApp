# Alertas de preço em segundo plano (GitHub Actions)

Até agora, o e-mail de alerta de preço-alvo só era verificado quando
**alguém clicava em "🔄 Atualizar Dados"** — no seu PC ou num dos
dashboards hospedados. Se ninguém abrisse o app num dia em que uma ação
caiu até o preço-alvo, você só ficaria sabendo quando abrisse o app de
novo.

Esta parte resolve isso: um robozinho roda sozinho, de hora em hora
(durante o horário do pregão da B3, de segunda a sexta), busca as
cotações e manda o e-mail de alerta na hora — mesmo com o PC desligado e
sem ninguém olhando o dashboard. Ele roda numa máquina do GitHub (de
graça), não no seu computador.

## Antes de começar

Isso só funciona depois de:

1. O repositório já estar publicado no GitHub (feito).
2. O celular/Firestore já estar configurado — isto é, você já tem o
   arquivo `firebase-service-account.json` (ver README_MOBILE.md).
3. O e-mail de alerta já estar configurado no seu PC — isto é, você já
   tem o arquivo `email_alertas.json` (feito, se você já recebeu algum
   alerta por e-mail antes).

Ambos os arquivos ficam na mesma pasta pessoal e protegida de sempre:
`~/.portfolio_b3_secrets` (fora da pasta do projeto).

## Por que preciso colar essas informações de novo?

O robozinho do GitHub Actions roda numa máquina nova a cada vez — sem a
sua pasta pessoal, sem o Firebase já conectado. Por isso ele precisa de
uma cópia dessas mesmas informações, guardada num cofre separado e
protegido do próprio GitHub, chamado **"Secrets"** (a mesma ideia já usada
no Passo 1 de README_HOSPEDAGEM.md, só que agora no GitHub em vez do
Streamlit Cloud) — nunca no código, nunca visível para ninguém depois de
salvo (nem para você mesmo — só dá pra substituir, não pra ver de novo).

## Passo 1: abrir os dois arquivos que você já tem

1. Abra a pasta `~/.portfolio_b3_secrets` no seu computador (no Explorador
   de Arquivos, cole `%USERPROFILE%\.portfolio_b3_secrets` na barra de
   endereço e aperte Enter).
2. Abra `firebase-service-account.json` com o Bloco de Notas — deixe essa
   janela aberta.
3. Abra `email_alertas.json` com o Bloco de Notas também — deixe essa
   janela aberta também.

## Passo 2: criar os 4 Secrets no GitHub

1. Acesse
   [https://github.com/dgcr2711-cloud/PortfolioApp/settings/secrets/actions](https://github.com/dgcr2711-cloud/PortfolioApp/settings/secrets/actions)
   (entre com sua conta do GitHub, se pedir).
2. Clique em **"New repository secret"**.
3. Crie o primeiro, com estes valores exatos:
   - **Name**: `FIREBASE_SERVICE_ACCOUNT_JSON`
   - **Secret**: cole **todo o conteúdo** do arquivo
     `firebase-service-account.json` (Ctrl+A, Ctrl+C nele, Ctrl+V aqui) —
     o arquivo inteiro, com as chaves `{ }` e tudo mais.
4. Clique em **"Add secret"**.
5. Repita "New repository secret" mais 3 vezes, uma para cada linha do
   arquivo `email_alertas.json`:
   - **Name**: `EMAIL_ALERTA_REMETENTE` — **Secret**: o valor de
     `"remetente"` nesse arquivo (só o e-mail, sem aspas).
   - **Name**: `EMAIL_ALERTA_SENHA_APP` — **Secret**: o valor de
     `"senha_app"` nesse arquivo (só a senha de app, sem aspas).
   - **Name**: `EMAIL_ALERTA_DESTINATARIO` — **Secret**: o valor de
     `"destinatario"` nesse arquivo (só o e-mail, sem aspas).

Ao final, a tela deve mostrar 4 Secrets cadastrados:
`FIREBASE_SERVICE_ACCOUNT_JSON`, `EMAIL_ALERTA_REMETENTE`,
`EMAIL_ALERTA_SENHA_APP` e `EMAIL_ALERTA_DESTINATARIO`. Você não consegue
mais ver o conteúdo deles depois de salvos (só apagar e recadastrar, se
precisar trocar algum) — isso é proposital, é assim que o GitHub protege
esse cofre.

## Passo 3: testar uma vez, na mão

Não precisa esperar até a próxima hora cheia para saber se funcionou:

1. Acesse
   [https://github.com/dgcr2711-cloud/PortfolioApp/actions/workflows/verificar_alertas.yml](https://github.com/dgcr2711-cloud/PortfolioApp/actions/workflows/verificar_alertas.yml).
2. Clique no botão **"Run workflow"** (do lado direito), depois no botão
   verde **"Run workflow"** que aparece.
3. Espere uns 10-20 segundos e atualize a página — vai aparecer uma
   execução nova na lista, com uma bolinha amarela (rodando), depois
   verde (deu certo) ou vermelha (deu erro).
4. Clique nela para ver os detalhes — dentro de "Rodar a verificação de
   alertas" aparece uma mensagem tipo `[alertas] Verificação concluída. 0
   alerta(s) de e-mail enviado(s).` (0 é o normal, se nenhum dos seus
   alertas configurados tiver sido atingido agora).

Se a bolinha ficar vermelha, me manda um print da tela de detalhes que eu
te ajudo a diagnosticar.

## Coisas para saber

- **Horário**: roda de hora em hora, das 10h às 18h (horário de
  Brasília), de segunda a sexta — cobrindo o pregão da B3. Fora desse
  horário, nenhuma cotação nova estaria disponível mesmo, então não faz
  sentido rodar.
- **Custo**: zero. O GitHub Actions é de graça para repositórios
  públicos, sem limite de execuções.
- **Isso substitui o alerta de "Atualizar Dados"?** Não — os dois
  continuam funcionando, um não interfere no outro. Este aqui só cobre os
  horários em que ninguém abriu o app manualmente.
- **Onde ver o histórico de execuções**: sempre em
  [https://github.com/dgcr2711-cloud/PortfolioApp/actions/workflows/verificar_alertas.yml](https://github.com/dgcr2711-cloud/PortfolioApp/actions/workflows/verificar_alertas.yml).
- **Se um dia quiser trocar a senha de app do e-mail ou a chave do
  Firebase**: apague o Secret antigo correspondente em
  [https://github.com/dgcr2711-cloud/PortfolioApp/settings/secrets/actions](https://github.com/dgcr2711-cloud/PortfolioApp/settings/secrets/actions)
  e cadastre um novo com o mesmo nome e o valor atualizado.
- **Nunca cole o conteúdo desses arquivos aqui no chat comigo** — os
  Secrets do GitHub são o único lugar onde essas informações devem ir a
  partir de agora.
