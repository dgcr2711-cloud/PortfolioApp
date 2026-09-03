"""
Cria (ou troca) o usuário/senha que protegem o SITE NA NUVEM (ver
core/auth.py para o porquê e como isso funciona).

A senha que você digitar aqui é lida pelo próprio terminal do seu
computador, criptografada (hash) na hora, e só o resultado criptografado é
salvo em ~/.portfolio_b3_secrets/login_site.json — a senha em texto puro
nunca é gravada em nenhum arquivo, nunca sai do seu computador, e eu
(Claude) nunca a vejo.

Depois de rodar este script, falta 1 passo pra valer no site de verdade:
rodar "Gerar Secrets Streamlit.bat" e colar o resultado nos Secrets do seu
app em share.streamlit.io (mesmo processo que você já faz pra outras
configurações) — este script te lembra disso no final.

Como rodar: dê dois cliques em "Configurar Login do Site.bat".
"""

from __future__ import annotations

import datetime
import getpass
import json
import secrets as segredos_aleatorios
import traceback

from core.auth import CAMINHO_CONFIG_LOGIN
from core.config import PASTA_SEGREDOS

# 2026-09-03: a janela preta estava fechando sozinha antes de terminar (sem
# chegar a criar o login_site.json), sem nenhum erro visível pro usuário —
# provavelmente uma exceção não tratada em algum ponto das perguntas
# interativas. CAMINHO_LOG_ERRO guarda qualquer erro que aconteça daqui pra
# frente, e o bloco try/except lá embaixo garante que a janela SEMPRE espera
# uma tecla antes de fechar, mesmo em caso de erro — nunca mais deve fechar
# sozinha sem dar chance de ler o que aconteceu.
CAMINHO_LOG_ERRO = PASTA_SEGREDOS / "erro_configurar_login.txt"

try:
    import streamlit_authenticator as stauth
except ImportError:
    stauth = None  # type: ignore[assignment]

NOME_COOKIE = "portfolio_b3_auth"
DIAS_EXPIRACAO_COOKIE = 30


def _gerar_ou_reaproveitar_chave_cookie() -> str:
    """
    Se já existir uma configuração salva, reaproveita a MESMA chave de
    cookie de antes — assim, se você só está trocando a senha, quem já
    estava logado no site não é deslogado à toa. Só gera uma chave
    aleatória nova na primeira vez que este script roda.
    """
    if CAMINHO_CONFIG_LOGIN.exists():
        try:
            with open(CAMINHO_CONFIG_LOGIN, "r", encoding="utf-8") as f:
                config_existente = json.load(f)
            chave_existente = config_existente.get("cookie", {}).get("key")
            if chave_existente:
                return chave_existente
        except (OSError, json.JSONDecodeError):
            pass
    return segredos_aleatorios.token_hex(32)


def main() -> None:
    if stauth is None:
        print("A biblioteca 'streamlit-authenticator' ainda não está instalada.")
        print("Feche esta janela, dê um duplo-clique em 'Iniciar App.bat' uma vez")
        print("(ele instala bibliotecas novas sozinho quando precisa) e rode este")
        print("script de novo depois.")
        return

    print("=" * 60)
    print(" Configurar o login do site (protege o link público)")
    print("=" * 60)
    print()
    print("A senha que você digitar abaixo NÃO aparece na tela (por")
    print("segurança) e não é enviada pra mim (Claude) nem sai deste")
    print("computador em texto puro — só fica salva já criptografada.")
    print()

    usuario = input("Escolha um nome de usuário (sem espaço, ex: diego): ").strip()
    if not usuario:
        print("\nNome de usuário não pode ser vazio. Rode o script de novo.")
        return

    nome = input("Seu nome (aparece na tela de login, ex: Diego): ").strip() or usuario
    email = input("Seu e-mail (só identificação, não precisa ser um e-mail real): ").strip()

    while True:
        senha = getpass.getpass("Digite a senha (não aparece na tela): ")
        if len(senha) < 6:
            print("Use pelo menos 6 caracteres. Vamos tentar de novo.\n")
            continue
        senha_confirmacao = getpass.getpass("Digite a mesma senha de novo, pra confirmar: ")
        if senha != senha_confirmacao:
            print("As senhas não bateram. Vamos tentar de novo.\n")
            continue
        break

    credenciais = {
        "usernames": {
            usuario: {
                "email": email,
                "first_name": nome,
                "last_name": "",
                "password": senha,
                "roles": ["admin"],
                "failed_login_attempts": 0,
                "logged_in": False,
            }
        }
    }
    stauth.Hasher.hash_passwords(credenciais)

    config = {
        "credentials": credenciais,
        "cookie": {
            "name": NOME_COOKIE,
            "key": _gerar_ou_reaproveitar_chave_cookie(),
            "expiry_days": DIAS_EXPIRACAO_COOKIE,
        },
    }

    PASTA_SEGREDOS.mkdir(parents=True, exist_ok=True)
    with open(CAMINHO_CONFIG_LOGIN, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print()
    print("=" * 60)
    print(f"Pronto! Login configurado (usuário: {usuario}).")
    print("Salvo em: " + str(CAMINHO_CONFIG_LOGIN))
    print("=" * 60)
    print()
    print("Falta 1 passo: esse login só vale no SITE NA NUVEM, ainda não")
    print("no seu PC (de propósito — ver core/auth.py). Pra ativar de vez:")
    print("  1. Dê um duplo-clique em 'Gerar Secrets Streamlit.bat'.")
    print("  2. Abra o arquivo que ele gerar, copie tudo (Ctrl+A, Ctrl+C).")
    print("  3. Cole em share.streamlit.io -> seu app -> Settings -> Secrets")
    print("     (substituindo o texto que já estava lá).")
    print()
    print(f"Guarde o usuário ({usuario}) e a senha em algum lugar seguro —")
    print("por exemplo seu gerenciador de senhas. Eu não tenho e não devo ter")
    print("acesso a ela.")


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
