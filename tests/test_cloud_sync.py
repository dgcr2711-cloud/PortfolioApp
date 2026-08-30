"""
Testes automatizados de core/cloud_sync.py — cobre só a parte pura e
testável sem precisar do pacote firebase_admin nem de rede: o fallback que
lê a chave do Firebase dos "Secrets" do Streamlit Community Cloud
(2026-08-30), usado quando o dashboard está hospedado e não existe a pasta
pessoal do PC (~/.portfolio_b3_secrets).

As funções que de fato falam com o Firestore (sincronizar_snapshot,
salvar/carregar_dados_completos_na_nuvem, buscar/marcar_pendencia...) não
têm teste automatizado aqui pelo mesmo motivo de sempre: dependem do
pacote firebase_admin (não instalado neste ambiente de testes) e de uma
chave de serviço de verdade — o jeito de validar essas continua sendo
manual, no seu PC, como já era antes desta mudança.

Rode com `pytest -v` (ver instruções em tests/test_calculations.py).
"""

from __future__ import annotations

import sys

from core import cloud_sync


class _FalsoModuloStreamlit:
    """Dublê mínimo do módulo `streamlit`, só com o atributo `secrets` (um
    dict) — usado pra testar o fallback sem precisar instalar o streamlit
    de verdade nem rodar dentro de um app Streamlit."""

    def __init__(self, secrets: dict):
        self.secrets = secrets


def _com_streamlit_falso(secrets: dict | None, testar):
    """
    Insere um módulo `streamlit` falso em sys.modules (ou garante que não
    exista nenhum, se secrets=None, simulando o streamlit não instalado)
    durante a chamada de `testar`, e sempre restaura o estado original —
    mesmo se `testar` lançar.
    """
    tinha_streamlit = "streamlit" in sys.modules
    streamlit_original = sys.modules.get("streamlit")
    if secrets is None:
        sys.modules.pop("streamlit", None)
    else:
        sys.modules["streamlit"] = _FalsoModuloStreamlit(secrets)
    try:
        testar()
    finally:
        if tinha_streamlit:
            sys.modules["streamlit"] = streamlit_original
        else:
            sys.modules.pop("streamlit", None)


_CHAVE_FIREBASE_FALSA = {
    "type": "service_account",
    "project_id": "meu-projeto-teste",
    "private_key": "-----BEGIN PRIVATE KEY-----\nfalsa\n-----END PRIVATE KEY-----\n",
    "client_email": "teste@meu-projeto-teste.iam.gserviceaccount.com",
}


def test_sem_streamlit_instalado_nao_encontra_credenciais():
    def testar():
        assert cloud_sync._obter_credenciais_dict_do_streamlit() is None

    _com_streamlit_falso(None, testar)


def test_com_streamlit_mas_sem_a_chave_configurada_retorna_none():
    def testar():
        assert cloud_sync._obter_credenciais_dict_do_streamlit() is None

    _com_streamlit_falso({"outra_coisa": {}}, testar)


def test_com_credenciais_configuradas_nos_secrets_devolve_o_dicionario():
    def testar():
        resultado = cloud_sync._obter_credenciais_dict_do_streamlit()
        assert resultado == _CHAVE_FIREBASE_FALSA

    _com_streamlit_falso({"firebase_service_account": _CHAVE_FIREBASE_FALSA}, testar)


def test_erro_inesperado_ao_ler_secrets_do_streamlit_nao_quebra():
    """Simula qualquer problema inesperado ao acessar st.secrets (ex:
    streamlit instalado mas rodando fora de um app de verdade) — nunca
    deve lançar exceção, só retornar None."""

    class ModuloQueBoia:
        @property
        def secrets(self):
            raise RuntimeError("não há um app Streamlit rodando")

    tinha_streamlit = "streamlit" in sys.modules
    streamlit_original = sys.modules.get("streamlit")
    sys.modules["streamlit"] = ModuloQueBoia()
    try:
        assert cloud_sync._obter_credenciais_dict_do_streamlit() is None
    finally:
        if tinha_streamlit:
            sys.modules["streamlit"] = streamlit_original
        else:
            sys.modules.pop("streamlit", None)
