# Instruções do projeto: PortfolioApp

## Contexto
Este workspace mistura:
- backend em Python no diretório `core/`
- UI desktop em Streamlit em `ui/`
- app mobile em React Native/Expo em `mobile-app/`
- testes em `tests/`

A prioridade é manter o sistema funcional, com alterações pequenas, verificáveis e alinhadas ao padrão do projeto.

## Regras gerais
- Sempre investigar a causa raiz antes de corrigir.
- Preferir mudanças mínimas e locais, sem refatorações amplas.
- Trabalhar em uma tarefa por vez; não abrir escopo novo sem necessidade.
- Quando houver erro, reproduzir ou validar antes de propor solução.
- Não inventar APIs, estruturas ou convenções que não existam no projeto.
- Respeitar o idioma do projeto: comentários e mensagens em português, quando já forem do padrão atual.

## Python / Streamlit
- Edits em `core/` e `ui/` devem seguir o estilo já usado no projeto.
- Preferir funções e módulos existentes em vez de reescrever lógica.
- Sempre validar com testes focados quando houver bug ou mudança relevante.
- Use `pytest` para testes Python, preferindo o arquivo mais específico do módulo afetado.

## Mobile / React Native
- Mantenha compatibilidade com Expo/React Native já configurado.
- Evitar dependências novas sem necessidade.
- Confirmar TypeScript com `npx tsc --noEmit` antes de considerar a mudança concluída.
- Respeitar as tipagens existentes e não silenciar erros sem entender a causa.

## Verificação antes de concluir
- Nunca afirmar que está funcionando sem evidência real.
- Sempre rodar a validação mais direta do comportamento alterado.
- Se existir teste específico, usá-lo antes de um sweep maior.
- Se não existir teste, validar com a checagem relevante do módulo afetado.

## Fluxo preferido para o Copilot
1. ler o ponto exato do problema
2. identificar a causa raiz
3. aplicar correção mínima
4. validar com comando focado
5. relatar o resultado com evidência

## Diretórios importantes
- `core/`: lógica de negócio e dados
- `ui/`: telas do app desktop
- `mobile-app/`: app móvel
- `tests/`: validação automatizada

## Objetivo principal
Maximizar produtividade sem perder confiabilidade: preferir correções pequenas, testadas e bem entendidas, em vez de soluções amplas e pouco verificadas.
