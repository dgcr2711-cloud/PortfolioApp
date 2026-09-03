"""
Gera o texto pronto para colar no painel "Secrets" do Streamlit Community
Cloud, a partir dos arquivos de configuração que você já tem em
~/.portfolio_b3_secrets/ (a mesma chave do Firebase e a mesma configuração
de e-mail que o app do PC já usa).

Por que isso existe: o Streamlit Cloud não lê arquivos da sua pasta pessoal
(~/.portfolio_b3_secrets) — o dashboard hospedado roda num computador da
Streamlit, não no seu. Lá, esse tipo de informação sensível é colado
diretamente no site, num formato de texto chamado TOML. Copiar a chave do
Firebase à mão pro formato certo é fácil de errar (ela tem várias linhas)
— este script monta o texto certinho, pronto pra copiar e colar, sem você
precisar entender TOML nem mexer numa vírgula.

O que ele NÃO faz: não envia nada pela internet, não fala com o Firebase,
não fala com o Streamlit. Só LÊ os arquivos que já existem no seu
computador e ESCREVE o resultado num outro arquivo de texto, também dentro
da pasta pessoal protegida (~/.portfolio_b3_secrets) — nunca dentro da
pasta do projeto, pra nunca ir parar no GitHub por engano.

Como rodar: dê dois cliques em "Gerar Secrets Streamlit.bat".
"""

from __future__ import annotations

import json
from typing import Any

from core.auth import CAMINHO_CONFIG_LOGIN
from core.cloud_sync import CAMINHO_CHAVE_FIREBASE
from core.config import CAMINHO_CHAVE_HGBRASIL, PASTA_SEGREDOS
from core.notificacoes_email import CAMINHO_CONFIG_EMAIL
from core.notificacoes_whatsapp import CAMINHO_CONFIG_WHATSAPP

NOME_ARQUIVO_SAIDA = "secrets_streamlit_gerado.txt"


def _valor_toml(valor: Any) -> str:
    """
    Formata um valor Python como um valor TOML válido. Strings com quebra
    de linha (caso clássico: a private_key da chave do Firebase, que tem
    várias linhas) usam aspas triplas, que aceitam a quebra de linha
    literal sem precisar escapar nada — as demais strings usam o mesmo
    escapamento de aspas/barras que o JSON já usa (compatível com TOML
    para os campos simples que aparecem aqui: e-mails, ids, URLs).
    """
    if isinstance(valor, str) and "\n" in valor:
        return f'"""{valor}"""'
    return json.dumps(valor)


def _secao_toml(nome_secao: str, dados: dict) -> str:
    linhas = [f"[{nome_secao}]"]
    for chave, valor in dados.items():
        linhas.append(f"{chave} = {_valor_toml(valor)}")
    return "\n".join(linhas)


def _secao_login_toml(config: dict) -> str:
    """
    O login (ver core/auth.py) tem uma estrutura ANINHADA (usuário dentro
    de credentials.usernames, mais uma seção cookie separada), diferente
    das outras seções acima (que são só chave = valor soltos) — por isso
    tem sua própria função em vez de reaproveitar _secao_toml.
    """
    linhas: list[str] = []
    usernames = config.get("credentials", {}).get("usernames", {})
    for usuario, dados_usuario in usernames.items():
        linhas.append(f"[login_site.credentials.usernames.{usuario}]")
        for chave, valor in dados_usuario.items():
            linhas.append(f"{chave} = {_valor_toml(valor)}")
        linhas.append("")

    cookie = config.get("cookie", {})
    linhas.append("[login_site.cookie]")
    for chave, valor in cookie.items():
        linhas.append(f"{chave} = {_valor_toml(valor)}")

    return "\n".join(linhas)


def gerar_texto_secrets() -> str:
    """Monta o texto TOML completo a partir dos arquivos que existirem. Nunca lança exceção por um arquivo faltando — só avisa no texto gerado."""
    blocos = [
        "# Cole TODO o conteúdo deste arquivo no painel Secrets do seu app,",
        "# em share.streamlit.io -> seu app -> Settings -> Secrets.",
        "# Gerado automaticamente por gerar_secrets_streamlit.py a partir dos",
        "# arquivos que já existem em " + str(PASTA_SEGREDOS),
    ]

    if CAMINHO_CHAVE_FIREBASE.exists():
        try:
            with open(CAMINHO_CHAVE_FIREBASE, "r", encoding="utf-8") as f:
                chave_firebase = json.load(f)
            blocos.append("")
            blocos.append(_secao_toml("firebase_service_account", chave_firebase))
        except (OSError, json.JSONDecodeError) as erro:
            blocos.append("")
            blocos.append(f"# Não consegui ler {CAMINHO_CHAVE_FIREBASE}: {erro}")
    else:
        blocos.append("")
        blocos.append(f"# Nenhuma chave do Firebase encontrada em {CAMINHO_CHAVE_FIREBASE} (celular/nuvem não configurados ainda)")

    if CAMINHO_CONFIG_EMAIL.exists():
        try:
            with open(CAMINHO_CONFIG_EMAIL, "r", encoding="utf-8") as f:
                config_email = json.load(f)
            blocos.append("")
            blocos.append(_secao_toml("email_alertas", config_email))
        except (OSError, json.JSONDecodeError) as erro:
            blocos.append("")
            blocos.append(f"# Não consegui ler {CAMINHO_CONFIG_EMAIL}: {erro}")
    else:
        blocos.append("")
        blocos.append(f"# Nenhuma configuração de e-mail encontrada em {CAMINHO_CONFIG_EMAIL} (alerta por e-mail não configurado ainda)")

    if CAMINHO_CONFIG_WHATSAPP.exists():
        try:
            with open(CAMINHO_CONFIG_WHATSAPP, "r", encoding="utf-8") as f:
                config_whatsapp = json.load(f)
            blocos.append("")
            blocos.append(_secao_toml("whatsapp_alertas", config_whatsapp))
        except (OSError, json.JSONDecodeError) as erro:
            blocos.append("")
            blocos.append(f"# Não consegui ler {CAMINHO_CONFIG_WHATSAPP}: {erro}")
    else:
        blocos.append("")
        blocos.append(f"# Nenhuma configuração de WhatsApp encontrada em {CAMINHO_CONFIG_WHATSAPP} (alerta por WhatsApp não configurado ainda)")

    if CAMINHO_CHAVE_HGBRASIL.exists():
        try:
            with open(CAMINHO_CHAVE_HGBRASIL, "r", encoding="utf-8") as f:
                chave_hgbrasil = json.load(f)
            blocos.append("")
            blocos.append(_secao_toml("hgbrasil", chave_hgbrasil))
        except (OSError, json.JSONDecodeError) as erro:
            blocos.append("")
            blocos.append(f"# Não consegui ler {CAMINHO_CHAVE_HGBRASIL}: {erro}")
    else:
        blocos.append("")
        blocos.append(f"# Nenhuma chave da HG Brasil encontrada em {CAMINHO_CHAVE_HGBRASIL} (taxas SELIC/CDI não configuradas ainda — rode 'Configurar Chave HG Brasil.bat' se quiser)")

    if CAMINHO_CONFIG_LOGIN.exists():
        try:
            with open(CAMINHO_CONFIG_LOGIN, "r", encoding="utf-8") as f:
                config_login = json.load(f)
            blocos.append("")
            blocos.append(_secao_login_toml(config_login))
        except (OSError, json.JSONDecodeError) as erro:
            blocos.append("")
            blocos.append(f"# Não consegui ler {CAMINHO_CONFIG_LOGIN}: {erro}")
    else:
        blocos.append("")
        blocos.append(f"# Nenhum login configurado em {CAMINHO_CONFIG_LOGIN} (site ainda abre sem senha — rode 'Configurar Login do Site.bat' se quiser proteger)")

    return "\n".join(blocos) + "\n"


if __name__ == "__main__":
    texto = gerar_texto_secrets()
    caminho_saida = PASTA_SEGREDOS / NOME_ARQUIVO_SAIDA
    PASTA_SEGREDOS.mkdir(parents=True, exist_ok=True)
    with open(caminho_saida, "w", encoding="utf-8") as f:
        f.write(texto)

    print("=" * 60)
    print("Pronto! O texto para colar no Streamlit Cloud foi salvo em:")
    print(str(caminho_saida))
    print("=" * 60)
    print()
    print("Abra esse arquivo com o Bloco de Notas, selecione tudo")
    print("(Ctrl+A), copie (Ctrl+C), e cole no painel Secrets do seu")
    print("app em share.streamlit.io -> seu app -> Settings -> Secrets.")
