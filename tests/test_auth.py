"""
Testes automatizados de core/auth.py: só a parte lógica pura,
_carregar_credenciais_da_nuvem() — que lê a seção [login_site] de
st.secrets (colada nos Secrets do Streamlit Community Cloud, ver
gerar_secrets_streamlit.py) e converte pro formato que o
streamlit-authenticator espera.

A parte de tela (exigir_login/mostrar_botao_sair — que chama
st.session_state, st.error, st.stop() etc.) não tem teste automatizado
aqui, pelo mesmo motivo de sempre: depende do streamlit rodando um app de
verdade (não do streamlit em si, que dá pra simular) pra fazer sentido —
verificado manualmente com screenshots reais do Diego, como o resto de
ui/.

Este módulo importa `streamlit` no TOPO do arquivo (core/auth.py faz
`import streamlit as st` no topo dele, igual core/market_data.py e
core/fundamentals.py — ver as docstrings desses dois arquivos de teste
pra entender por quê) — e "test_auth.py" vem ANTES de "test_calculations.py",
"test_fundamentals.py" e "test_market_data.py" em ordem alfabética (ver
/tmp/rodar_testes_sandbox.py), então é ESTE arquivo que registra o módulo
streamlit falso primeiro — o `sys.modules.setdefault(...)` dos outros vira
no-op, e todos acabam reaproveitando o dublê definido aqui. Por isso o
dublê abaixo também precisa expor `cache_data` (usado por
market_data.py/fundamentals.py), não só `secrets` (usado por este arquivo)
— senão a importação desses outros módulos, mais tarde na mesma rodada de
testes, quebraria.

Rode com `pytest -v` (ver instruções em tests/test_calculations.py).
"""

from __future__ import annotations

import sys


class _FalsoDecoradorCacheData:
    """Mesmo dublê usado em test_market_data.py/test_fundamentals.py —
    substitui @st.cache_data(...) por um decorador que não faz cache
    nenhum, com um `.clear()` de mentira."""

    def __call__(self, *args, **kwargs):
        def decorador(func):
            def wrapper(*a, **kw):
                return func(*a, **kw)
            wrapper.clear = lambda: None
            return wrapper
        return decorador


class _FalsoModuloStreamlit:
    cache_data = _FalsoDecoradorCacheData()

    def __init__(self):
        self.secrets: dict = {}


sys.modules.setdefault("streamlit", _FalsoModuloStreamlit())

from core import auth  # noqa: E402  (import depois de injetar o módulo falso, de propósito)


def _com_secrets(secrets: dict, testar):
    """Troca auth.st.secrets pelo dict de teste durante a chamada de
    `testar`, sempre restaurando pra {} no final — mesmo se `testar`
    lançar."""
    original = auth.st.secrets
    auth.st.secrets = secrets
    try:
        testar()
    finally:
        auth.st.secrets = original


_LOGIN_VALIDO = {
    "login_site": {
        "credentials": {
            "usernames": {
                "diego": {
                    "email": "diego@exemplo.com",
                    "first_name": "Diego",
                    "last_name": "",
                    "password": "$2b$12$hashfalso",
                    "roles": ["admin"],
                    "failed_login_attempts": 0,
                    "logged_in": False,
                }
            }
        },
        "cookie": {"name": "portfolio_b3_auth", "key": "chavefalsa123", "expiry_days": 30},
    }
}


def test_sem_login_site_nos_secrets_devolve_none():
    def testar():
        assert auth._carregar_credenciais_da_nuvem() is None

    _com_secrets({}, testar)


def test_com_login_site_bem_formado_devolve_estrutura_convertida():
    def testar():
        resultado = auth._carregar_credenciais_da_nuvem()
        assert resultado is not None
        assert resultado["cookie"]["name"] == "portfolio_b3_auth"
        assert resultado["cookie"]["key"] == "chavefalsa123"
        assert resultado["cookie"]["expiry_days"] == 30
        assert resultado["credentials"]["usernames"]["diego"]["email"] == "diego@exemplo.com"
        assert resultado["credentials"]["usernames"]["diego"]["password"] == "$2b$12$hashfalso"
        # devolve dicts/listas comuns, não os objetos originais aninhados —
        # importante porque o streamlit-authenticator espera dict de verdade
        assert isinstance(resultado["credentials"]["usernames"]["diego"], dict)

    _com_secrets(_LOGIN_VALIDO, testar)


def test_com_varios_usuarios_converte_todos():
    secrets = {
        "login_site": {
            "credentials": {
                "usernames": {
                    "diego": {"email": "diego@exemplo.com", "password": "hash1"},
                    "convidado": {"email": "convidado@exemplo.com", "password": "hash2"},
                }
            },
            "cookie": {"name": "portfolio_b3_auth", "key": "chavefalsa", "expiry_days": 30},
        }
    }

    def testar():
        resultado = auth._carregar_credenciais_da_nuvem()
        usernames = resultado["credentials"]["usernames"]
        assert set(usernames.keys()) == {"diego", "convidado"}
        assert usernames["convidado"]["email"] == "convidado@exemplo.com"

    _com_secrets(secrets, testar)


def test_login_site_mal_formado_devolve_none_sem_quebrar():
    """Falta a seção "cookie" inteira — não deve lançar exceção, só voltar None."""
    secrets_quebrado = {
        "login_site": {
            "credentials": {"usernames": {"diego": {"password": "hash1"}}},
            # sem "cookie" de propósito
        }
    }

    def testar():
        assert auth._carregar_credenciais_da_nuvem() is None

    _com_secrets(secrets_quebrado, testar)


def test_login_site_com_usernames_faltando_devolve_none_sem_quebrar():
    secrets_quebrado = {
        "login_site": {
            "credentials": {},  # sem "usernames" dentro
            "cookie": {"name": "x", "key": "y", "expiry_days": 30},
        }
    }

    def testar():
        assert auth._carregar_credenciais_da_nuvem() is None

    _com_secrets(secrets_quebrado, testar)


def test_erro_inesperado_ao_ler_secrets_nao_quebra():
    """Simula qualquer problema inesperado (ex: st.secrets acessado fora de
    um app Streamlit de verdade) — nunca deve lançar, só devolver None."""

    class SecretsQueBoia:
        def __contains__(self, chave):
            raise RuntimeError("não há um app Streamlit rodando")

    original = auth.st.secrets
    auth.st.secrets = SecretsQueBoia()
    try:
        assert auth._carregar_credenciais_da_nuvem() is None
    finally:
        auth.st.secrets = original
