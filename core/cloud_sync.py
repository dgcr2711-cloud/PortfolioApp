"""
Sincronização com a nuvem (Firebase Firestore) para o app do celular.

Arquitetura escolhida: o app do PC continua sendo o ÚNICO lugar onde você
registra compras, define preço teto etc. — a "fonte da verdade" continua
sendo data/portfolio_data.json, exatamente como sempre foi. A única coisa
nova é que, toda vez que você clica em "🔄 Atualizar Dados", além de salvar
localmente, o app também envia um retrato (snapshot) resumido e já
calculado da carteira para o Firestore — e é só esse retrato que o app do
celular lê (core/mobile_snapshot.py monta esse retrato).

Por que essa arquitetura, e não o celular buscando cotações sozinho?
Porque assim nenhuma fórmula financeira (preço médio, preço teto, HHI de
concentração...) precisa ser reescrita numa segunda linguagem — o celular
só EXIBE um número que o PC já calculou e já testamos.

Requer um arquivo de chave de serviço (JSON) baixado do Console do
Firebase — ver README_MOBILE.md para o passo a passo de como gerar essa
chave. Se o arquivo não existir, a sincronização é silenciosamente
ignorada, e o app continua funcionando 100% normalmente sem o celular —
ninguém é obrigado a configurar isso.

IMPORTANTE: o pacote `firebase-admin` só é importado aqui dentro, na hora
em que a chave existir e a sincronização for de fato tentada — assim, no
seu PC, quem não configurar o app do celular nem percebe essa biblioteca
(o app funciona normalmente sem ela).

Nota (2026-08-30): `firebase-admin` PASSOU a estar também no
requirements.txt principal (além de requirements-mobile.txt), porque o
dashboard hospedado no Streamlit Community Cloud usa exatamente este
arquivo para sincronizar com o Firestore — sem ela lá, o app hospedado
quebra com "ModuleNotFoundError". No seu PC isso só significa uma
biblioteca a mais instalada; nada muda no comportamento.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
from typing import Any

from core.config import PASTA_RAIZ, PASTA_SEGREDOS

# Local ATUAL da chave: fora da pasta do projeto (ver PASTA_SEGREDOS em
# core/config.py — motivo detalhado lá). Local ANTIGO: dentro da própria
# pasta do projeto, onde a chave ficava até 2026-08-30 — mantido aqui só
# para a migração automática abaixo encontrar e mover uma chave já existente.
CAMINHO_CHAVE_FIREBASE = PASTA_SEGREDOS / "firebase-service-account.json"
_CAMINHO_CHAVE_FIREBASE_ANTIGO = PASTA_RAIZ / "firebase-service-account.json"
COLECAO_FIRESTORE = "portfolio"
DOCUMENTO_FIRESTORE = "snapshot"

# Documento SEPARADO do "snapshot" acima — este guarda os dados BRUTOS e
# editáveis (o mesmo formato de core.data_store.estrutura_padrao(): compras,
# alertas, preços-teto...), não um resumo já calculado. É o que faz o
# Firestore virar a "fonte de verdade" de verdade (2026-08-30): qualquer
# lugar que rode este app — o PC, um dashboard hospedado na nuvem, um
# script de segundo plano — lê e escreve aqui, em vez de cada um ter sua
# própria cópia local desatualizada. O celular continua lendo só o
# "snapshot" resumido acima; ele nunca precisa (nem deve) ler o bruto.
DOCUMENTO_DADOS_COMPLETOS = "dados_completos"

# Coleções separadas onde o app do celular deposita "pedidos" (nova
# compra/venda, remover uma transação, calcular um preço teto — ver
# core/pendencias_celular.py). Em todas elas, as regras de segurança do
# Firestore só deixam o celular CRIAR um documento e LER esse documento
# específico pelo id (pra acompanhar pendente -> aplicado/erro); listar a
# coleção inteira, alterar ou apagar só o SDK Admin (este arquivo, rodando
# no PC) pode fazer.
COLECAO_PENDENCIAS = "pendencias_compras"
COLECAO_PENDENCIAS_REMOCOES = "pendencias_remocoes"
COLECAO_PENDENCIAS_PRECO_TETO = "pendencias_preco_teto"
COLECAO_PENDENCIAS_TESE = "pendencias_teses"

_app_inicializado = False
_migracao_ja_tentada = False


def _migrar_chave_antiga_se_necessario() -> None:
    """
    Correção de segurança (2026-08-30): a chave do Firebase costumava ficar
    dentro da pasta do projeto — um risco real caso essa pasta um dia seja
    copiada, enviada a alguém, ou vire um repositório Git. Se encontrar uma
    chave no local antigo e nenhuma ainda no local novo (fora da pasta do
    projeto), move automaticamente, sem exigir nenhuma ação manual.

    Roda no máximo uma vez por execução do app (`_migracao_ja_tentada`) e
    nunca lança exceção: numa falha (ex: sem permissão de escrita na pasta
    pessoal), o app simplesmente continua lendo a chave do local antigo até
    a próxima tentativa.
    """
    global _migracao_ja_tentada
    if _migracao_ja_tentada:
        return
    _migracao_ja_tentada = True

    if CAMINHO_CHAVE_FIREBASE.exists() or not _CAMINHO_CHAVE_FIREBASE_ANTIGO.exists():
        return
    try:
        PASTA_SEGREDOS.mkdir(parents=True, exist_ok=True)
        shutil.move(str(_CAMINHO_CHAVE_FIREBASE_ANTIGO), str(CAMINHO_CHAVE_FIREBASE))
        try:
            # Restringe a leitura do arquivo só ao dono (sem efeito real no
            # Windows, mas correto e inofensivo também rodar lá).
            CAMINHO_CHAVE_FIREBASE.chmod(stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass
        print(
            f"[segurança] Chave do Firebase movida de {_CAMINHO_CHAVE_FIREBASE_ANTIGO} "
            f"para {CAMINHO_CHAVE_FIREBASE} (fora da pasta do projeto)."
        )
    except OSError:
        pass


def sincronizacao_configurada() -> bool:
    """True se o arquivo de chave do Firebase existe (ou seja, se o usuário já configurou o app do celular)."""
    _migrar_chave_antiga_se_necessario()
    return CAMINHO_CHAVE_FIREBASE.exists() or _CAMINHO_CHAVE_FIREBASE_ANTIGO.exists()


_VARIAVEL_AMBIENTE_CHAVE_FIREBASE = "FIREBASE_SERVICE_ACCOUNT_JSON"


def _obter_credenciais_dict_da_variavel_de_ambiente() -> dict[str, Any] | None:
    """
    Fallback usado pelo script de segundo plano do GitHub Actions
    (2026-08-30 — ver scripts/verificar_alertas_segundo_plano.py e
    .github/workflows/verificar_alertas.yml): lá não existe nem a pasta
    pessoal do PC nem um app Streamlit de verdade rodando (então nem a
    chave em arquivo nem os Secrets do Streamlit Cloud estão disponíveis),
    então a chave do Firebase é colada inteira, como texto JSON numa linha
    só, num "Secret" do próprio repositório do GitHub (Settings -> Secrets
    and variables -> Actions -> New repository secret), sob o nome
    FIREBASE_SERVICE_ACCOUNT_JSON — nunca no código, nunca commitado.

    Retorna None sem erro nenhum se a variável não existir (uso normal no
    PC ou num app Streamlit hospedado) ou se o conteúdo não for um JSON
    válido (erro de configuração — melhor cair no "não configurado" do que
    quebrar o script inteiro).
    """
    bruto = os.environ.get(_VARIAVEL_AMBIENTE_CHAVE_FIREBASE)
    if not bruto:
        return None
    try:
        credenciais = json.loads(bruto)
    except json.JSONDecodeError:
        return None
    return credenciais if isinstance(credenciais, dict) else None


def _obter_credenciais_dict_do_streamlit() -> dict[str, Any] | None:
    """
    Fallback usado quando este código roda HOSPEDADO no Streamlit Community
    Cloud (2026-08-30) — lá não existe a pasta pessoal do seu PC
    (~/.portfolio_b3_secrets), então a chave do Firebase é colada no painel
    "Secrets" do próprio app, no site do Streamlit Cloud (nunca no código,
    nunca no GitHub), sob a chave [firebase_service_account]. Ver
    README_HOSPEDAGEM.md para o passo a passo de como colar isso lá.

    Retorna None sem erro nenhum em qualquer um destes casos: rodando no
    PC (a chave já vem do arquivo, ver _garantir_firebase_inicializado),
    rodando fora de um app Streamlit de verdade (ex: um script de segundo
    plano no GitHub Actions), ou streamlit nem estando instalado.
    """
    try:
        import streamlit as st

        if "firebase_service_account" in st.secrets:
            return dict(st.secrets["firebase_service_account"])
    except Exception:
        pass
    return None


def _garantir_firebase_inicializado() -> bool:
    """
    Inicializa a conexão com o Firebase uma única vez por execução do app.
    Tenta, nesta ordem: (1) a chave em arquivo local (uso normal no seu
    PC), (2) a variável de ambiente FIREBASE_SERVICE_ACCOUNT_JSON (script
    de segundo plano no GitHub Actions, 2026-08-30 — ver
    _obter_credenciais_dict_da_variavel_de_ambiente), (3) os "Secrets" do
    Streamlit Cloud (uso hospedado — ver _obter_credenciais_dict_do_streamlit).
    Retorna False se nenhuma das três estiver disponível.
    """
    global _app_inicializado
    if _app_inicializado:
        return True

    if sincronizacao_configurada():
        # Depois de sincronizacao_configurada() já ter tentado migrar, usa
        # a chave nova se ela existir; se a migração falhou por algum
        # motivo, cai para o local antigo em vez de travar a sincronização.
        caminho_chave = CAMINHO_CHAVE_FIREBASE if CAMINHO_CHAVE_FIREBASE.exists() else _CAMINHO_CHAVE_FIREBASE_ANTIGO
        origem_credenciais: str | dict[str, Any] = str(caminho_chave)
    else:
        credenciais_do_ambiente = _obter_credenciais_dict_da_variavel_de_ambiente()
        if credenciais_do_ambiente is not None:
            origem_credenciais = credenciais_do_ambiente
        else:
            credenciais_do_streamlit = _obter_credenciais_dict_do_streamlit()
            if credenciais_do_streamlit is None:
                return False
            origem_credenciais = credenciais_do_streamlit

    import firebase_admin
    from firebase_admin import credentials

    if not firebase_admin._apps:
        cred = credentials.Certificate(origem_credenciais)
        firebase_admin.initialize_app(cred)
    _app_inicializado = True
    return True


def sincronizar_snapshot(snapshot: dict[str, Any]) -> bool:
    """
    Envia o retrato atual da carteira para o Firestore. Retorna True se
    enviou com sucesso, False se a sincronização não está configurada ou
    se algo deu errado (sem internet, chave inválida etc.).

    Nunca lança uma exceção: sincronizar com o celular é um "extra" — uma
    falha aqui não pode travar a atualização de cotações no PC, que é a
    função principal do botão.
    """
    if not _garantir_firebase_inicializado():
        return False
    try:
        from firebase_admin import firestore

        db = firestore.client()
        db.collection(COLECAO_FIRESTORE).document(DOCUMENTO_FIRESTORE).set(snapshot)
        return True
    except Exception:
        return False


def salvar_dados_completos_na_nuvem(dados: dict[str, Any]) -> bool:
    """
    Envia o dicionário de dados COMPLETO (o mesmo formato de
    core.data_store.estrutura_padrao()) para o Firestore — ver o comentário
    em DOCUMENTO_DADOS_COMPLETOS acima. Chamado por
    core.data_store.salvar_dados() a cada gravação, como um "espelho na
    nuvem" best-effort.

    Retorna True se enviou com sucesso, False se a sincronização não está
    configurada ou se algo deu errado (sem internet, chave inválida etc.).
    Nunca lança exceção: a gravação LOCAL (a que realmente importa pro app
    continuar funcionando) já aconteceu antes desta chamada — uma falha
    aqui não pode derrubar nada.
    """
    if not _garantir_firebase_inicializado():
        return False
    try:
        from firebase_admin import firestore

        db = firestore.client()
        db.collection(COLECAO_FIRESTORE).document(DOCUMENTO_DADOS_COMPLETOS).set(dados)
        return True
    except Exception:
        return False


def carregar_dados_completos_da_nuvem() -> dict[str, Any] | None:
    """
    Lê o dicionário de dados completo do Firestore (ver
    salvar_dados_completos_na_nuvem). Retorna None se a sincronização não
    estiver configurada, estiver inacessível (sem internet), ou se o
    documento ainda não existir por lá (primeira vez rodando o app depois
    desta atualização, ou celular/nuvem nunca configurados) — em qualquer
    um desses casos, quem chamou deve usar o arquivo local como alternativa
    (é exatamente o que core.data_store.carregar_dados() faz).
    """
    if not _garantir_firebase_inicializado():
        return None
    try:
        from firebase_admin import firestore

        db = firestore.client()
        documento = db.collection(COLECAO_FIRESTORE).document(DOCUMENTO_DADOS_COMPLETOS).get()
        if not documento.exists:
            return None
        return documento.to_dict()
    except Exception:
        return None


def buscar_pendencias_pendentes(colecao: str = COLECAO_PENDENCIAS) -> list[dict[str, Any]]:
    """
    Busca no Firestore os pedidos criados pelo celular numa coleção de
    pendência (compra/venda, remoção ou cálculo de preço teto) que ainda
    não foram aplicados (status == "pendente"). Cada item vem com um campo
    extra "_id" (o id do documento no Firestore), usado depois para marcar
    como aplicado/erro com marcar_pendencia().

    Nunca lança exceção: sem internet ou sem sincronização configurada, só
    retorna lista vazia — o app continua funcionando normalmente sem o celular.
    """
    if not _garantir_firebase_inicializado():
        return []
    try:
        from firebase_admin import firestore

        db = firestore.client()
        documentos = db.collection(colecao).where("status", "==", "pendente").stream()
        pendencias = []
        for documento in documentos:
            item = documento.to_dict() or {}
            item["_id"] = documento.id
            pendencias.append(item)
        return pendencias
    except Exception:
        return []


def marcar_pendencia(
    doc_id: str, status: str, mensagem_erro: str | None = None,
    colecao: str = COLECAO_PENDENCIAS, campos_extra: dict[str, Any] | None = None,
) -> None:
    """Atualiza o status de um pedido do celular (aplicado/erro) depois de processá-lo,
    opcionalmente gravando campos extra no mesmo documento (ex: o resultado calculado
    da calculadora de preço teto, pra o celular exibir sem precisar de outra consulta).
    Nunca lança exceção — se falhar, o pior caso é o celular continuar mostrando
    "pendente" um pouco mais, sem travar o app do PC."""
    if not _garantir_firebase_inicializado():
        return
    try:
        from firebase_admin import firestore

        db = firestore.client()
        atualizacao: dict[str, Any] = {"status": status}
        if mensagem_erro is not None:
            atualizacao["mensagemErro"] = mensagem_erro
        if campos_extra:
            atualizacao.update(campos_extra)
        db.collection(colecao).document(doc_id).update(atualizacao)
    except Exception:
        pass
