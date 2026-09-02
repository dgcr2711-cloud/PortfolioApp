"""
Testes automatizados de gerar_secrets_streamlit.py — o script que
transforma a chave do Firebase e a configuração de e-mail que já existem
localmente (~/.portfolio_b3_secrets) no texto TOML que vai colado no
painel "Secrets" do Streamlit Community Cloud (2026-08-30).

Como sempre, nenhum teste aqui toca nos arquivos reais em
~/.portfolio_b3_secrets: os caminhos são redirecionados manualmente pra
arquivos temporários (sem fixtures/monkeypatch do pytest — ver o padrão em
tests/test_notificacoes_email.py) e sempre restaurados no final.

Rode com `pytest -v` (ver instruções em tests/test_calculations.py).
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import gerar_secrets_streamlit as gerador


def test_valor_toml_string_simples_usa_aspas_duplas_normais():
    assert gerador._valor_toml("abc@gmail.com") == '"abc@gmail.com"'


def test_valor_toml_numero():
    assert gerador._valor_toml(465) == "465"


def test_valor_toml_string_multilinha_usa_aspas_triplas():
    valor = "-----BEGIN PRIVATE KEY-----\nMIIfalsa\n-----END PRIVATE KEY-----\n"
    resultado = gerador._valor_toml(valor)
    assert resultado.startswith('"""')
    assert resultado.endswith('"""')
    assert "-----BEGIN PRIVATE KEY-----" in resultado
    assert "\\n" not in resultado  # quebra de linha real, não escapada


def test_secao_toml_monta_cabecalho_e_uma_linha_por_chave():
    resultado = gerador._secao_toml("email_alertas", {"remetente": "a@a.com", "porta_smtp": 465})
    linhas = resultado.splitlines()
    assert linhas[0] == "[email_alertas]"
    assert 'remetente = "a@a.com"' in linhas
    assert "porta_smtp = 465" in linhas


def test_secao_login_toml_monta_usuario_aninhado_e_secao_cookie():
    config = {
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
    resultado = gerador._secao_login_toml(config)
    linhas = resultado.splitlines()

    assert "[login_site.credentials.usernames.diego]" in linhas
    assert 'email = "diego@exemplo.com"' in linhas
    assert 'password = "$2b$12$hashfalso"' in linhas
    assert 'roles = ["admin"]' in linhas
    assert "failed_login_attempts = 0" in linhas
    assert "logged_in = false" in linhas  # bool Python -> minúsculo em TOML/JSON

    assert "[login_site.cookie]" in linhas
    assert 'name = "portfolio_b3_auth"' in linhas
    assert 'key = "chavefalsa123"' in linhas
    assert "expiry_days = 30" in linhas


def test_secao_login_toml_varios_usuarios_cada_um_com_seu_proprio_cabecalho():
    config = {
        "credentials": {
            "usernames": {
                "diego": {"email": "diego@exemplo.com", "password": "hash1"},
                "convidado": {"email": "convidado@exemplo.com", "password": "hash2"},
            }
        },
        "cookie": {"name": "portfolio_b3_auth", "key": "chavefalsa", "expiry_days": 30},
    }
    resultado = gerador._secao_login_toml(config)
    assert "[login_site.credentials.usernames.diego]" in resultado
    assert "[login_site.credentials.usernames.convidado]" in resultado


def _com_caminhos_isolados(
    testar,
    conteudo_firebase: dict | None,
    conteudo_email: dict | None,
    conteudo_whatsapp: dict | None = None,
    conteudo_login: dict | None = None,
):
    """
    Redireciona gerador.CAMINHO_CHAVE_FIREBASE, gerador.CAMINHO_CONFIG_EMAIL,
    gerador.CAMINHO_CONFIG_WHATSAPP e gerador.CAMINHO_CONFIG_LOGIN pra
    arquivos temporários (criando-os só se o conteúdo correspondente não for
    None) durante a chamada de `testar`, e sempre restaura os valores
    originais — mesmo se `testar` lançar.
    """
    chave_original = gerador.CAMINHO_CHAVE_FIREBASE
    email_original = gerador.CAMINHO_CONFIG_EMAIL
    whatsapp_original = gerador.CAMINHO_CONFIG_WHATSAPP
    login_original = gerador.CAMINHO_CONFIG_LOGIN
    with tempfile.TemporaryDirectory() as pasta_tmp:
        pasta = Path(pasta_tmp)
        caminho_chave = pasta / "firebase-service-account.json"
        caminho_email = pasta / "email_alertas.json"
        caminho_whatsapp = pasta / "whatsapp_alertas.json"
        caminho_login = pasta / "login_site.json"
        if conteudo_firebase is not None:
            caminho_chave.write_text(json.dumps(conteudo_firebase), encoding="utf-8")
        if conteudo_email is not None:
            caminho_email.write_text(json.dumps(conteudo_email), encoding="utf-8")
        if conteudo_whatsapp is not None:
            caminho_whatsapp.write_text(json.dumps(conteudo_whatsapp), encoding="utf-8")
        if conteudo_login is not None:
            caminho_login.write_text(json.dumps(conteudo_login), encoding="utf-8")

        gerador.CAMINHO_CHAVE_FIREBASE = caminho_chave
        gerador.CAMINHO_CONFIG_EMAIL = caminho_email
        gerador.CAMINHO_CONFIG_WHATSAPP = caminho_whatsapp
        gerador.CAMINHO_CONFIG_LOGIN = caminho_login
        try:
            testar()
        finally:
            gerador.CAMINHO_CHAVE_FIREBASE = chave_original
            gerador.CAMINHO_CONFIG_EMAIL = email_original
            gerador.CAMINHO_CONFIG_WHATSAPP = whatsapp_original
            gerador.CAMINHO_CONFIG_LOGIN = login_original


def test_gerar_texto_secrets_sem_nenhum_arquivo_configurado_avisa_e_nao_quebra():
    def testar():
        texto = gerador.gerar_texto_secrets()
        assert "[firebase_service_account]" not in texto
        assert "[email_alertas]" not in texto
        assert "[whatsapp_alertas]" not in texto
        assert "[login_site" not in texto
        assert "Nenhuma chave do Firebase encontrada" in texto
        assert "Nenhuma configuração de e-mail encontrada" in texto
        assert "Nenhuma configuração de WhatsApp encontrada" in texto
        assert "Nenhum login configurado" in texto

    _com_caminhos_isolados(testar, conteudo_firebase=None, conteudo_email=None, conteudo_whatsapp=None, conteudo_login=None)


def test_gerar_texto_secrets_com_login_inclui_secao_login_site():
    login_falso = {
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
        "cookie": {"name": "portfolio_b3_auth", "key": "chavefalsa", "expiry_days": 30},
    }

    def testar():
        texto = gerador.gerar_texto_secrets()
        assert "[login_site.credentials.usernames.diego]" in texto
        assert 'password = "$2b$12$hashfalso"' in texto
        assert "[login_site.cookie]" in texto
        assert "Nenhum login configurado" not in texto

    _com_caminhos_isolados(testar, conteudo_firebase=None, conteudo_email=None, conteudo_whatsapp=None, conteudo_login=login_falso)


def test_gerar_texto_secrets_com_todos_os_arquivos_monta_as_tres_secoes():
    chave_falsa = {
        "type": "service_account",
        "project_id": "meu-projeto",
        "private_key": "-----BEGIN PRIVATE KEY-----\nfalsa\n-----END PRIVATE KEY-----\n",
        "client_email": "conta@meu-projeto.iam.gserviceaccount.com",
    }
    email_falso = {"remetente": "voce@gmail.com", "senha_app": "abcd efgh", "destinatario": "voce@gmail.com"}
    whatsapp_falso = {"numero": "+5511999999999", "apikey": "123456"}

    def testar():
        texto = gerador.gerar_texto_secrets()

        assert "[firebase_service_account]" in texto
        assert 'project_id = "meu-projeto"' in texto
        assert '"""' in texto  # private_key multi-linha usando aspas triplas
        assert "-----BEGIN PRIVATE KEY-----" in texto

        assert "[email_alertas]" in texto
        assert 'remetente = "voce@gmail.com"' in texto

        assert "[whatsapp_alertas]" in texto
        assert 'numero = "+5511999999999"' in texto
        assert 'apikey = "123456"' in texto

        assert "Nenhuma" not in texto  # nenhum aviso de arquivo faltando, já que os três existem

    _com_caminhos_isolados(testar, conteudo_firebase=chave_falsa, conteudo_email=email_falso, conteudo_whatsapp=whatsapp_falso)


def test_gerar_texto_secrets_so_com_email_nao_inclui_as_outras_secoes():
    email_falso = {"remetente": "voce@gmail.com", "senha_app": "abcd", "destinatario": "voce@gmail.com"}

    def testar():
        texto = gerador.gerar_texto_secrets()
        assert "[firebase_service_account]" not in texto
        assert "Nenhuma chave do Firebase encontrada" in texto
        assert "[email_alertas]" in texto
        assert "[whatsapp_alertas]" not in texto
        assert "Nenhuma configuração de WhatsApp encontrada" in texto

    _com_caminhos_isolados(testar, conteudo_firebase=None, conteudo_email=email_falso, conteudo_whatsapp=None)


def test_gerar_texto_secrets_so_com_whatsapp_nao_inclui_as_outras_secoes():
    whatsapp_falso = {"numero": "+5511999999999", "apikey": "123456"}

    def testar():
        texto = gerador.gerar_texto_secrets()
        assert "[firebase_service_account]" not in texto
        assert "[email_alertas]" not in texto
        assert "Nenhuma configuração de e-mail encontrada" in texto
        assert "[whatsapp_alertas]" in texto
        assert 'numero = "+5511999999999"' in texto

    _com_caminhos_isolados(testar, conteudo_firebase=None, conteudo_email=None, conteudo_whatsapp=whatsapp_falso)
