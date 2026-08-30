# Meu Portfólio B3 no celular — o que falta fazer

Boa notícia: eu já fiz tudo que dava pra fazer sem estar na sua frente. O projeto do Firebase já está criado, o banco de dados já está configurado com as regras de segurança, a chave de acesso já está salva (o app move automaticamente para uma pasta fora do projeto na primeira vez que abre, por segurança — ver `core/cloud_sync.py` se quiser conferir), e o arquivo `mobile-app/src/firebase.ts` já está preenchido com as chaves de configuração reais do seu projeto.

Só sobraram **2 comandos pra rodar no seu computador** (não tenho acesso ao terminal da sua máquina) e **1 app pra instalar no celular**. Uns 5 minutos.

## Parte 1 — Ligar o app do PC à nuvem (~1 min)

1. Abra um terminal na pasta `PortfolioApp`, ative o ambiente virtual (`venv\Scripts\activate`) e rode:
   ```
   pip install -r requirements-mobile.txt
   ```
2. Pronto — da próxima vez que clicar em "🔄 Atualizar Dados" no app do PC, vai aparecer "📱 Sincronizado com o celular" na mensagem.

## Parte 2 — Rodar o app no celular (~4 min)

1. No celular: instale o app grátis **Expo Go** (Play Store no Android / App Store no iPhone).
2. No PC, abra um terminal **dentro de** `PortfolioApp/mobile-app` e rode, nessa ordem:
   ```
   npm install
   npx expo start
   ```
3. Vai aparecer um QR code no terminal.
   - **Android:** abra o Expo Go e escaneie.
   - **iPhone:** abra a Câmera nativa, aponte pro QR, toque no aviso que aparece pra abrir no Expo Go.
4. O app abre na tela "Visão Geral". Se disser "Nenhum dado sincronizado ainda", volte no PC e clique em "🔄 Atualizar Dados" uma vez — o celular atualiza sozinho.

---

**Se travar em algum comando ou aparecer um erro**, me manda a mensagem de erro exata (foto ou texto) que eu resolvo — não precisa tentar descobrir sozinho.

**Sobre a Apple (resumo):** Expo Go é de graça e não expira — é por isso que estamos usando ele. Um app "de verdade" na tela (sem abrir pelo Expo Go) exigiria a conta paga da Apple (~US$99/ano). No Android dá pra chegar nesse resultado de graça mais pra frente (posso te ajudar quando quiser: `npx eas build -p android`).

**Novidade (2026-08-30): Diário de Tese de Investimento, com uma etapa manual pendente.** Adicionei uma aba nova no PC ("📓 Diário de Tese") e no celular ("Mais → 📓") para anotar por que você comprou (ou está de olho em) cada ativo — a lista de notas de cada ativo aparece nos dois lugares. Só que, diferente das outras novidades, **esta depende de uma regra nova no Firestore que só você consegue adicionar** (preciso das suas credenciais do Console do Firebase, que eu não tenho e não devo pedir). Sem isso, escrever uma nota pelo CELULAR fica "pendente" para sempre — ler o diário e escrever pelo PC funciona normalmente de qualquer forma.

Como adicionar a regra (2 minutos, só uma vez):
1. Abra [console.firebase.google.com](https://console.firebase.google.com/), entre no projeto `meu-portfolio-b3`.
2. No menu à esquerda: Firestore Database → aba "Regras" (Rules).
3. Procure o bloco parecido com este, que já deve existir para o Preço Teto:
   ```
   match /pendencias_preco_teto/{docId} {
     allow create: if true;
     allow get: if true;
     allow list, update, delete: if false;
   }
   ```
4. Logo abaixo dele (dentro do mesmo bloco `match /databases/{database}/documents { ... }`), cole este novo bloco:
   ```
   match /pendencias_teses/{docId} {
     allow create: if true;
     allow get: if true;
     allow list, update, delete: if false;
   }
   ```
5. Clique em "Publicar" (Publish).

Se o bloco do Preço Teto no seu console estiver com um formato diferente do exemplo acima, copie exatamente o formato que você já tem, só trocando o nome da coleção para `pendencias_teses` — o importante é que a nova regra tenha as mesmas permissões da que já existe.

**Novidade (2026-08-30): PIN de acesso.** Na próxima vez que abrir o app no celular, ele vai perguntar se você quer criar um PIN de 4 dígitos — se aceitar, o app passa a pedir esse PIN toda vez que for aberto (inclusive quando volta de segundo plano, tipo quando você troca de app ou destrava o celular). Pode ativar, trocar ou remover isso a qualquer momento em "Mais → 🔒". Importante: é uma tranca só na TELA do celular — não substitui a segurança dos dados na nuvem (isso é um projeto maior, registrado à parte).

**O que ficou de fora por enquanto:** o celular só mostra a carteira — registrar compra nova continua sendo no PC.

**Novidade (2026-08-30): login anônimo do Firebase, com 2 etapas manuais pendentes.** Esta é a parte "maior" de segurança que ficou registrada à parte quando implementei o PIN de acesso (ver nota acima) — o PIN tranca a TELA do celular, mas até agora os dados na nuvem ficavam protegidos só pela configuração do projeto ficar "escondida" dentro do app (que, por natureza, nunca é 100% escondida — é assim que todo app com Firebase funciona). A partir de agora, o próprio app do celular faz um "login anônimo" no Firebase assim que abre — não pede e-mail, senha nem nenhuma informação sua, é só uma identidade técnica que o Firebase dá ao aparelho — e eu já preparei as regras do Firestore no código para EXIGIR esse login. Só que, como da última vez, **as regras de verdade só você consegue publicar** (preciso das suas credenciais do Console do Firebase, que eu não tenho e não devo pedir).

Sem estas 2 etapas, o app do celular vai parar de funcionar (vai ficar preso na tela branca de "conectando") assim que você atualizar os arquivos — então faça as duas ANTES de abrir o app atualizado:

**Etapa 1 — Ativar o login anônimo (1 minuto):**
1. Abra [console.firebase.google.com](https://console.firebase.google.com/), entre no projeto `meu-portfolio-b3`.
2. No menu à esquerda: Authentication (Autenticação) → aba "Sign-in method" (Métodos de login). Se for a primeira vez usando esta seção, clique em "Get started" (Começar) primeiro.
3. Na lista de provedores, clique em "Anonymous" (Anônimo), ative o interruptor e clique em "Save" (Salvar).

**Etapa 2 — Atualizar as regras do Firestore (2 minutos):**
1. No mesmo Console, vá em Firestore Database → aba "Regras" (Rules).
2. Você vai ver blocos parecidos com estes (o formato exato pode variar um pouco do seu):
   ```
   match /portfolio/{docId} {
     allow read: if true;
     allow write: if false;
   }
   match /pendencias_compras/{docId} {
     allow create: if true;
     allow get: if true;
     allow list, update, delete: if false;
   }
   ```
   (e o mesmo padrão `allow create: if true; allow get: if true;` se repete para `pendencias_remocoes`, `pendencias_preco_teto` e `pendencias_teses`.)
3. Troque **todo** `if true` que aparecer nesses blocos (o do `portfolio` e o das 4 coleções `pendencias_*`) para `if request.auth != null`. Ou seja, o bloco do `portfolio` fica:
   ```
   match /portfolio/{docId} {
     allow read: if request.auth != null;
     allow write: if false;
   }
   ```
   e cada bloco de `pendencias_*` fica:
   ```
   match /pendencias_compras/{docId} {
     allow create: if request.auth != null;
     allow get: if request.auth != null;
     allow list, update, delete: if false;
   }
   ```
   **Não mexa** em nenhum `if false` — esses continuam exatamente como estão.
4. Clique em "Publicar" (Publish).

**Por que isso é mais seguro:** antes, qualquer pessoa que descobrisse a configuração pública do projeto (o conteúdo de `mobile-app/src/firebase.ts` — que, reforçando, é público por natureza em qualquer app com Firebase, não é um vazamento) conseguiria ler seu patrimônio e criar pendências direto no banco, sem nunca ter o app instalado. Depois desta mudança, só quem tem o app de verdade (que faz o login anônimo automaticamente) consegue. O app do PC continua funcionando exatamente igual — ele usa a chave de serviço (SDK Admin), que ignora essas regras e nunca precisou de login anônimo.

Se travar em algum desses passos ou aparecer um erro no celular depois, me manda a mensagem de erro exata (foto ou texto) que eu resolvo.

**Novidade (2026-08-30): login com e-mail e senha, substituindo o login anônimo — com 2 etapas manuais pendentes.** Depois de implementar o login anônimo (nota acima), você pediu para trocar pelo login do Google "por questão de segurança". Pesquisei antes de sair programando e encontrei um problema real: o Google exige, hoje em dia, que o app saia do Expo Go (o jeito que usamos para testar o app de graça) e vá para uma "build de desenvolvimento" própria — o que custa US$99/ano só na conta de desenvolvedor da Apple, para poder instalar no iPhone. Como você respondeu "sem preferência" quando te expliquei essa troca, segui com a alternativa que dá a MESMA segurança de verdade, sem esse custo: login com e-mail e senha.

**Por que é tão seguro quanto o Google:** hoje (login anônimo) qualquer pessoa que abrir o app pela primeira vez ganha uma "conta" válida sozinha — o Firebase não sabe se é você. Com e-mail e senha, só existe UMA conta de verdade: a que você mesmo vai criar agora, com o e-mail e a senha que você escolher. As regras do Firestore vão travar o acesso pelo seu UID específico (um código único daquela conta) — ou seja, só quem sabe seu e-mail E sua senha consegue ler ou escrever seus dados na nuvem. Isso é a mesma proteção que o login do Google daria, só que sem precisar sair do Expo Go.

Sem estas 2 etapas, o app do celular vai ficar preso na tela de login (o que é esperado — só não vai ter como entrar até você criar a conta):

**Etapa 1 — Ativar o login por e-mail/senha (1 minuto):**
1. Abra [console.firebase.google.com](https://console.firebase.google.com/), entre no projeto `meu-portfolio-b3`.
2. No menu à esquerda: Authentication (Autenticação) → aba "Sign-in method" (Métodos de login).
3. Na lista de provedores, clique em "Email/Password" (E-mail/senha), ative o interruptor de cima ("Email/Password", não precisa do "Email link") e clique em "Save" (Salvar).

**Etapa 2 — Criar sua conta (1 minuto):**
1. Ainda em Authentication, clique na aba "Users" (Usuários).
2. Clique em "Add user" (Adicionar usuário).
3. Digite um e-mail (não precisa ser um e-mail real que você usa — pode ser até um e-mail "de mentira" tipo `voce@exemplo.com`, já que ninguém vai te mandar mensagem nele; o que importa é você guardar esse e-mail e a senha) e uma senha (guarde os dois, por exemplo no seu gerenciador de senhas — eu não tenho acesso e não devo saber a senha).
4. Clique em "Add user" para confirmar.

Depois de fazer as duas etapas, me avisa ("feito") que eu confirmo do meu lado (lendo só o UID da conta que aparece na lista — sem ver e-mail nem senha) e te mando o texto final das regras do Firestore para você publicar (mesmo processo de copiar e colar de antes).

**O que muda no celular:** ao abrir o app atualizado, em vez do login anônimo automático, vai aparecer uma tela pedindo e-mail e senha — use os que você acabou de criar. A sessão fica salva no aparelho depois do primeiro login (não pede de novo toda vez). Para sair, use "Mais → 🔒 → Sair da conta".

**Sobre o login anônimo antigo:** pode deixar ativado no Console sem problema (não é obrigatório desativar) — depois que as regras novas exigirem o UID específico da sua conta, uma conta anônima não vai conseguir acessar nada mesmo. É só um provedor "sobrando", inofensivo.
