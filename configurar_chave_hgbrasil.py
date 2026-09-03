"""
Salva a chave da API da HG Brasil Finance (https://hgbrasil.com/finance/) —
usada para buscar as taxas SELIC/CDI e, como plano B, cotações de
ações/FIIs quando o Yahoo Finance falhar (ver core/market_data.py).

A chave é lida aqui, salva em ~/.portfolio_b3_secrets/hgbrasil_api_key.json
— fora da pasta do projeto, mesmo local/motivo de sempre (nunca ir parar
no GitHub por engano) — e nunca é enviada pra mim (Claude) nem sai deste
computador.

Onde pegar sua chave: entre em https://console.hgbrasil.com/, faça login
na conta que você já tem, e copie a chave (token) da API "Finance" — ela
costuma aparecer na tela inicial do painel, em "Minhas Aplicações" ou
"API Keys".

Depois de rodar este script, falta 1 passo pra valer no site hospedado
também: rodar "Gerar Secrets Streamlit.bat" e colar o resultado nos
Secrets do seu app em share.streamlit.io (mesmo processo que você já faz
pra outras configurações) — este script te lembra disso no final.

Como rodar: dê dois cliques em "Configurar Chave HG Brasil.bat".
"""

from __future__ import annotations

import datetime
import json
import traceback

from core.config import CAMINHO_CHAVE_HGBRASIL, PASTA_SEGREDOS

CAMINHO_LOG_ERRO = PASTA_SEGREDOS / "erro_configurar_hgbrasil.txt"


def main() -> None:
    print("=" * 60)
    print(" Configurar a chave da API HG Brasil Finance")
    print("=" * 60)
    print()
    print("Se você ainda não tem uma chave: entre em")
    print("https://console.hgbrasil.com/, faça login na sua conta, e copie")
    print("a chave (token) da API 'Finance'.")
    print()

    chave = input("Cole aqui a sua chave da HG Brasil: ").strip()
    if not chave:
        print("\nChave não pode ser vazia. Rode o script de novo quando tiver a chave em mãos.")
        return

    PASTA_SEGREDOS.mkdir(parents=True, exist_ok=True)
    with open(CAMINHO_CHAVE_HGBRASIL, "w", encoding="utf-8") as f:
        json.dump({"api_key": chave}, f, ensure_ascii=False, indent=2)

    print()
    print("=" * 60)
    print("Pronto! Chave salva em:")
    print(str(CAMINHO_CHAVE_HGBRASIL))
    print("=" * 60)
    print()
    print("Já vale para o app no seu PC (Iniciar App.bat) na próxima vez que")
    print("você clicar em '🔄 Atualizar Dados'.")
    print()
    print("Falta 1 passo para valer também no SITE NA NUVEM:")
    print("  1. Dê um duplo-clique em 'Gerar Secrets Streamlit.bat'.")
    print("  2. Abra o arquivo que ele gerar, copie tudo (Ctrl+A, Ctrl+C).")
    print("  3. Cole em share.streamlit.io -> seu app -> Settings -> Secrets")
    print("     (substituindo o texto que já estava lá).")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\n\nCancelado. Nada foi salvo. Pode fechar esta janela.")
        input("\nPressione ENTER para fechar...")
    except Exception:
        erro_completo = traceback.format_exc()
        print("\n" + "=" * 60)
        print(" Deu um erro e o script parou antes de terminar.")
        print(" Nada foi salvo. Isso NÃO é sua culpa — é um problema")
        print(" no script, que já ficou registrado para eu corrigir.")
        print("=" * 60)
        print()
        print(erro_completo)
        try:
            PASTA_SEGREDOS.mkdir(parents=True, exist_ok=True)
            with open(CAMINHO_LOG_ERRO, "a", encoding="utf-8") as f:
                f.write(f"\n\n----- {datetime.datetime.now().isoformat()} -----\n")
                f.write(erro_completo)
        except OSError:
            pass
        input("\nPressione ENTER para fechar (o Claude já consegue ver esse erro)...")
