"""
Login do dashboard hospedado (e-mail/senha) — 2026-09-04.

Por que isso existe: o site na nuvem (Streamlit Community Cloud) hoje só é
protegido por ninguém saber o link — quem tiver o endereço consegue ver seus
dados reais, sem precisar de senha nenhuma. Isso adiciona uma tela de login
de verdade, usando a biblioteca `streamlit-authenticator` (hash de senha,
sem depender de nenhum provedor externo tipo Google).

Onde a configuração mora:
  - LOCAL (seu PC): `~/.portfolio_b3_secrets/login_site.json`, criado pelo
    "Configurar Login do Site.bat" — nunca dentro da pasta do projeto, pelo
    mesmo motivo de sempre (não ir parar no GitHub por engano).
  - NUVEM (Streamlit Cloud): colado em Settings -> Secrets, dentro da seção
    [login_site] — gerado a partir do arquivo local acima pelo já existente
    "Gerar Secrets Streamlit.bat" (ver gerar_secrets_streamlit.py).

Decisão importante: exigir_login() só verifica st.secrets (a configuração da
NUVEM), nunca o arquivo local. Isso é de propósito — o objetivo é proteger
o link público, não pedir senha toda vez que você mesmo abre o app no seu
próprio PC (Iniciar App.bat / localhost:8501, que já só você alcança). O
arquivo local existe só como "rascunho" pra gerar o texto da nuvem, igual
já acontece com a chave do Firebase e a configuração de e-mail/WhatsApp.

Se ainda não existir nenhuma configuração de login colada nos Secrets da
nuvem, o site continua abrindo normalmente sem pedir nada — assim isso
nunca tranca ninguém (nem você) fora do site antes de configurar o login de
propósito.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from core.config import PASTA_SEGREDOS

try:
    import streamlit_authenticator as stauth
except ImportError:  # biblioteca ainda não instalada (ex: venv desatualizado)
    stauth = None  # type: ignore[assignment]

# Onde a configuração LOCAL de login mora (usuário/e-mail/senha já com hash
# + a chave do cookie) — criado por configurar_login_site.py, lido por
# gerar_secrets_streamlit.py para montar o texto dos Secrets da nuvem. Não é
# usado por exigir_login() abaixo (ver docstring do módulo — o motivo é de
# propósito).
CAMINHO_CONFIG_LOGIN = PASTA_SEGREDOS / "login_site.json"


def _carregar_credenciais_da_nuvem() -> dict[str, Any] | None:
    """
    Lê a seção [login_site] de st.secrets (só existe se você já colou o
    texto gerado pelo "Gerar Secrets Streamlit.bat" nos Secrets do app
    hospedado). Devolve None em qualquer situação em que não dê pra usar
    (não configurado, formato inesperado, st.secrets indisponível) — nunca
    lança exceção, pra um problema aqui nunca derrubar o site inteiro.
    """
    try:
        if "login_site" not in st.secrets:
            return None
        bruto = dict(st.secrets["login_site"])
        # st.secrets devolve objetos "AttrDict" aninhados — convertendo
        # tudo pra dict/list comuns evita comportamento estranho dentro do
        # streamlit-authenticator, que espera dicts de verdade.
        return {
            "credentials": {
                "usernames": {
                    usuario: dict(valores)
                    for usuario, valores in dict(bruto["credentials"]["usernames"]).items()
                }
            },
            "cookie": dict(bruto["cookie"]),
        }
    except Exception:
        return None


def _login_obrigatorio_configurado() -> bool:
    """Indica se o app hospedado foi configurado para exigir login."""
    try:
        if "login_site" in st.secrets:
            return True
        return bool(st.secrets.get("seguranca", {}).get("exigir_login", False))
    except Exception:
        return False


def exigir_login() -> None:
    """
    Trava a tela até o login ser feito, SE houver configuração de login nos
    Secrets da nuvem. Chame isso bem no início de app.py, logo depois de
    st.set_page_config — antes de carregar ou desenhar qualquer dado real.
    """
    if not _login_obrigatorio_configurado():
        return

    if stauth is None:
        st.error("O login obrigatório está configurado, mas a biblioteca de autenticação não está instalada.")
        st.stop()

    credenciais = _carregar_credenciais_da_nuvem()
    if not credenciais:
        st.error("O login obrigatório está configurado, mas os Secrets de login estão inválidos ou incompletos.")
        st.stop()

    if "_authenticator" not in st.session_state:
        st.session_state["_authenticator"] = stauth.Authenticate(
            credenciais["credentials"],
            credenciais["cookie"]["name"],
            credenciais["cookie"]["key"],
            credenciais["cookie"]["expiry_days"],
        )
    authenticator = st.session_state["_authenticator"]

    try:
        authenticator.login()
    except Exception as erro:
        st.error(f"Não consegui abrir a tela de login: {erro}")
        st.stop()

    status = st.session_state.get("authentication_status")
    if status is False:
        st.error("Usuário ou senha incorretos.")
        st.stop()
    if status is None:
        st.info("Entre com seu usuário e senha para continuar.")
        st.stop()
    # status is True -> login certo, o app segue normalmente daqui pra baixo.


def mostrar_botao_sair() -> None:
    """
    Mostra o botão "Sair" (só aparece se o login estiver configurado e a
    pessoa já estiver logada) — chame de algum lugar sempre visível, tipo a
    barra lateral. Não faz nada (sem erro) se o login não estiver ativo.
    """
    authenticator = st.session_state.get("_authenticator")
    if authenticator is not None and st.session_state.get("authentication_status"):
        authenticator.logout("Sair", "sidebar")
