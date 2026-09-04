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
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
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

# Prazo máximo (segundos) para qualquer chamada de rede ao Firestore
# (2026-09-03 — antes disso não existia limite nenhum aqui). Sem isso, uma
# instabilidade de rede ou de autenticação (ex: logo depois de trocar a
# chave do Firebase, como aconteceu hoje) podia deixar o app TRAVADO com a
# tela em branco pra sempre: carregar_dados() é chamado ANTES de qualquer
# coisa aparecer na tela, e as chamadas ao Firestore não tinham prazo — se
# a chamada nunca falhasse nem nunca respondesse, o app também nunca
# terminava de carregar. Com o prazo, o pior caso vira "demora até
# TIMEOUT_FIRESTORE_SEGUNDOS e cai pro arquivo local automaticamente" (ver
# o "except Exception" logo abaixo de cada chamada), nunca mais uma tela
# em branco permanente.
TIMEOUT_FIRESTORE_SEGUNDOS = 10

# 2026-09-03 — reforço além do timeout= passado direto pro Firestore acima:
# a inicialização da conexão (_garantir_firebase_inicializado, chamada logo
# no começo de carregar_dados_completos_da_nuvem) também pode, em teoria,
# tentar uma verificação de rede por trás dos panos (bibliotecas de
# autenticação do Google às vezes tentam detectar "estou rodando dentro do
# Google Cloud?" antes mesmo da primeira chamada ao Firestore) — e isso NÃO
# é coberto pelo timeout= do Firestore, porque acontece antes dele. Rodar a
# função inteira (inicialização + busca) numa thread separada com um limite
# de tempo TOTAL garante, de um jeito à prova de qualquer detalhe interno
# dessas bibliotecas, que o app nunca mais fica esperando pra sempre —
# no pior caso, ele só demora até TIMEOUT_TOTAL_CARREGAR_NUVEM_SEGUNDOS e
# segue com o arquivo local, exatamente como se a nuvem estivesse fora do ar.
TIMEOUT_TOTAL_CARREGAR_NUVEM_SEGUNDOS = 12

# 2026-09-04 — Diego relatou "Atualizar Dados" ainda travado/muito lento
# mesmo depois de paralelizar as buscas de preço (core/market_data.py) e de
# proventos da B3 (core/b3_publico.py). Investigando de novo: `atualizar_dados`
# (ui/acoes_comuns.py) começa chamando buscar_pendencias_pendentes() para
# QUATRO coleções diferentes (compras, remoções, preço-teto, teses) EM
# SEQUÊNCIA, cada uma só protegida pelo `timeout=` passado direto pro SDK do
# Firestore (TIMEOUT_FIRESTORE_SEGUNDOS=10s) — 4 x 10s = até 40s só nessa
# etapa, ANTES de sequer começar a buscar cotações. Bate exatamente com o
# "já foram 40 seg" relatado.
#
# Pior: essa mesma proteção (timeout= sozinho) já foi comprovada
# INSUFICIENTE neste projeto (ver nota técnica de
# carregar_dados_completos_da_nuvem acima, 2026-09-03) — a inicialização da
# conexão com o Firebase (autenticação) roda ANTES da chamada em si e pode,
# em teoria, travar por tempo indefinido sem que nenhum `timeout=` do lado
# de dentro chegue a valer. Foi por isso que carregar_dados_completos_da_nuvem
# (e as buscas da HG Brasil em core/market_data.py) passaram a rodar dentro
# de uma thread com prazo TOTAL rígido — mas buscar_pendencias_pendentes,
# marcar_pendencia, sincronizar_snapshot e salvar_dados_completos_na_nuvem
# ainda não tinham recebido essa mesma proteção. Agora têm (ver
# _rodar_com_prazo_total abaixo, extraído do mesmo padrão comprovado).
TIMEOUT_TOTAL_OPERACAO_FIRESTORE_SEGUNDOS = 12


def _rodar_com_prazo_total(funcao_sem_argumentos, valor_padrao: Any = None) -> Any:
    """
    Roda `funcao_sem_argumentos` (sem parâmetros — use uma lambda/closure
    para passar argumentos) numa thread separada com um prazo TOTAL rígido
    de TIMEOUT_TOTAL_OPERACAO_FIRESTORE_SEGUNDOS. Mesmo padrão, já testado
    e comprovado, de carregar_dados_completos_da_nuvem (ver nota técnica
    ali sobre por que é `threading.Thread` + `daemon=True` + `join(timeout=)`,
    e NÃO `ThreadPoolExecutor` dentro de um `with` — o `with` espera a
    thread travada terminar ao sair do bloco, cancelando o timeout na
    prática).

    Devolve `valor_padrao` se a função não terminar a tempo — a thread
    trava "órfã" em segundo plano (daemon, nunca impede o app de seguir
    nem de fechar depois).
    """
    resultado_container: dict[str, Any] = {}

    def _trabalho() -> None:
        resultado_container["valor"] = funcao_sem_argumentos()

    thread = threading.Thread(target=_trabalho, daemon=True)
    thread.start()
    thread.join(timeout=TIMEOUT_TOTAL_OPERACAO_FIRESTORE_SEGUNDOS)
    return resultado_container.get("valor", valor_padrao)


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

    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(origem_credenciais)
            firebase_admin.initialize_app(cred)
    except Exception as erro:
        # 2026-09-05 — antes essa exceção (ex: credencial com campo
        # faltando/formato errado) não era pega em NENHUM lugar: ela
        # atravessava direto pra thread do _rodar_com_prazo_total (que só
        # devolve valor_padrao quando a função *termina* dentro do prazo,
        # não quando lança uma exceção) e virava um traceback cru de
        # "Exception in thread" no log, um por chamada — sem nunca dizer
        # com clareza que o problema era a credencial. Agora cai limpo em
        # "não configurado", igual às outras duas fontes de credencial.
        print(f"[cloud_sync] Credencial do Firebase inválida: {erro!r}")
        return False
    _app_inicializado = True
    return True


def _sincronizar_snapshot_sem_prazo(snapshot: dict[str, Any]) -> bool:
    """Faz o trabalho de verdade de sincronizar_snapshot() — separado para poder rodar dentro do prazo rígido de _rodar_com_prazo_total."""
    if not _garantir_firebase_inicializado():
        return False
    try:
        from firebase_admin import firestore

        db = firestore.client()
        db.collection(COLECAO_FIRESTORE).document(DOCUMENTO_FIRESTORE).set(snapshot, timeout=TIMEOUT_FIRESTORE_SEGUNDOS)
        return True
    except Exception as erro:
        # 2026-09-04 — diagnóstico temporário: imprime o motivo real da
        # falha (sem parar nada, sem mudar o retorno False) porque essa
        # falha estava totalmente muda no log do GitHub Actions — impossível
        # saber se era permissão, dado inválido ou timeout sem isso.
        print(f"[cloud_sync] Falha ao sincronizar snapshot com o Firestore: {erro!r}")
        return False


def sincronizar_snapshot(snapshot: dict[str, Any]) -> bool:
    """
    Envia o retrato atual da carteira para o Firestore. Retorna True se
    enviou com sucesso, False se a sincronização não está configurada, se
    algo deu errado (sem internet, chave inválida etc.), ou se demorou
    demais (2026-09-04 — ver TIMEOUT_TOTAL_OPERACAO_FIRESTORE_SEGUNDOS).

    Nunca trava nem lança uma exceção: sincronizar com o celular é um
    "extra" — uma falha ou demora aqui não pode travar a atualização de
    cotações no PC, que é a função principal do botão.
    """
    return bool(_rodar_com_prazo_total(lambda: _sincronizar_snapshot_sem_prazo(snapshot), valor_padrao=False))


def _salvar_dados_completos_na_nuvem_sem_prazo(dados: dict[str, Any]) -> bool:
    """Faz o trabalho de verdade de salvar_dados_completos_na_nuvem() — separado para poder rodar dentro do prazo rígido de _rodar_com_prazo_total."""
    if not _garantir_firebase_inicializado():
        return False
    try:
        from firebase_admin import firestore

        db = firestore.client()
        db.collection(COLECAO_FIRESTORE).document(DOCUMENTO_DADOS_COMPLETOS).set(dados, timeout=TIMEOUT_FIRESTORE_SEGUNDOS)
        return True
    except Exception as erro:
        # 2026-09-04 — mesmo diagnóstico temporário de _sincronizar_snapshot_sem_prazo acima.
        print(f"[cloud_sync] Falha ao salvar dados completos no Firestore: {erro!r}")
        return False


def salvar_dados_completos_na_nuvem(dados: dict[str, Any]) -> bool:
    """
    Envia o dicionário de dados COMPLETO (o mesmo formato de
    core.data_store.estrutura_padrao()) para o Firestore — ver o comentário
    em DOCUMENTO_DADOS_COMPLETOS acima. Chamado por
    core.data_store.salvar_dados() a cada gravação, como um "espelho na
    nuvem" best-effort.

    Retorna True se enviou com sucesso, False se a sincronização não está
    configurada, se algo deu errado (sem internet, chave inválida etc.), ou
    se demorou demais (2026-09-04 — ver TIMEOUT_TOTAL_OPERACAO_FIRESTORE_SEGUNDOS).
    Nunca trava nem lança exceção: a gravação LOCAL (a que realmente
    importa pro app continuar funcionando) já aconteceu antes desta
    chamada — uma falha ou demora aqui não pode derrubar nada.
    """
    return bool(_rodar_com_prazo_total(lambda: _salvar_dados_completos_na_nuvem_sem_prazo(dados), valor_padrao=False))


def _carregar_dados_completos_da_nuvem_sem_prazo() -> dict[str, Any] | None:
    """Faz o trabalho de verdade de carregar_dados_completos_da_nuvem() —
    separado numa função própria só para poder ser rodado dentro do prazo
    rígido de TIMEOUT_TOTAL_CARREGAR_NUVEM_SEGUNDOS logo abaixo."""
    if not _garantir_firebase_inicializado():
        return None
    try:
        from firebase_admin import firestore

        db = firestore.client()
        documento = db.collection(COLECAO_FIRESTORE).document(DOCUMENTO_DADOS_COMPLETOS).get(timeout=TIMEOUT_FIRESTORE_SEGUNDOS)
        if not documento.exists:
            return None
        return documento.to_dict()
    except Exception:
        return None


def carregar_dados_completos_da_nuvem() -> dict[str, Any] | None:
    """
    Lê o dicionário de dados completo do Firestore (ver
    salvar_dados_completos_na_nuvem). Retorna None se a sincronização não
    estiver configurada, estiver inacessível (sem internet), demorar demais
    (mais de TIMEOUT_TOTAL_CARREGAR_NUVEM_SEGUNDOS — ver comentário na
    constante), ou se o documento ainda não existir por lá (primeira vez
    rodando o app depois desta atualização, ou celular/nuvem nunca
    configurados) — em qualquer um desses casos, quem chamou deve usar o
    arquivo local como alternativa (é exatamente o que
    core.data_store.carregar_dados() faz). Esta função é chamada bem no
    início do app, ANTES de qualquer coisa aparecer na tela — por isso o
    cuidado extra pra nunca travar por tempo indefinido.

    Nota técnica (2026-09-03): a primeira versão desta proteção usava
    `ThreadPoolExecutor` dentro de um `with` — parecia certo e até
    funcionava sozinha, mas testei de verdade (não só assumi) e descobri
    que o PRÓPRIO `with` espera a thread travada terminar ao sair do bloco
    (`shutdown(wait=True)` por padrão), cancelando o timeout na prática.
    Por isso a troca para uma `threading.Thread` com `daemon=True`: essa,
    sim, comprovadamente devolve o controle no prazo certo (testei os dois
    jeitos lado a lado antes de trocar).
    """
    resultado_container: dict[str, Any] = {}

    def _trabalho() -> None:
        resultado_container["valor"] = _carregar_dados_completos_da_nuvem_sem_prazo()

    thread = threading.Thread(target=_trabalho, daemon=True)
    thread.start()
    thread.join(timeout=TIMEOUT_TOTAL_CARREGAR_NUVEM_SEGUNDOS)
    # Se "valor" não estiver no dicionário, a thread não terminou a tempo —
    # ela continua rodando "órfã" em segundo plano (uma thread daemon nunca
    # impede o app de seguir em frente nem de fechar depois), e o app usa
    # o arquivo local, exatamente como se a nuvem estivesse fora do ar.
    return resultado_container.get("valor")


def _buscar_pendencias_pendentes_sem_prazo(colecao: str) -> list[dict[str, Any]]:
    """Faz o trabalho de verdade de buscar_pendencias_pendentes() — separado para poder rodar dentro do prazo rígido de _rodar_com_prazo_total."""
    if not _garantir_firebase_inicializado():
        return []
    try:
        from firebase_admin import firestore
        from google.cloud.firestore_v1.base_query import FieldFilter

        db = firestore.client()
        # 2026-09-05 — .where("status", "==", "pendente") (3 argumentos
        # posicionais) é a API antiga do google-cloud-firestore; funciona,
        # mas gera um UserWarning em TODO log só de existir. FieldFilter é
        # a forma atual — elimina o aviso na raiz (não é só cosmético:
        # a forma antiga também será removida numa versão futura da
        # biblioteca, então trocar agora evita quebrar o robô mais adiante).
        documentos = (
            db.collection(colecao)
            .where(filter=FieldFilter("status", "==", "pendente"))
            .stream(timeout=TIMEOUT_FIRESTORE_SEGUNDOS)
        )
        pendencias = []
        for documento in documentos:
            item = documento.to_dict() or {}
            item["_id"] = documento.id
            pendencias.append(item)
        return pendencias
    except Exception:
        return []


def buscar_pendencias_pendentes(colecao: str = COLECAO_PENDENCIAS) -> list[dict[str, Any]]:
    """
    Busca no Firestore os pedidos criados pelo celular numa coleção de
    pendência (compra/venda, remoção ou cálculo de preço teto) que ainda
    não foram aplicados (status == "pendente"). Cada item vem com um campo
    extra "_id" (o id do documento no Firestore), usado depois para marcar
    como aplicado/erro com marcar_pendencia().

    Nunca trava nem lança exceção: sem internet, sem sincronização
    configurada, ou demorando demais (2026-09-04 — chamada dentro de
    _rodar_com_prazo_total; ver comentário em
    TIMEOUT_TOTAL_OPERACAO_FIRESTORE_SEGUNDOS sobre por que isso importa
    especialmente aqui — "Atualizar Dados" chama esta função para 4
    coleções diferentes, EM SEQUÊNCIA, logo no início), só retorna lista
    vazia — o app continua funcionando normalmente sem o celular.
    """
    return _rodar_com_prazo_total(lambda: _buscar_pendencias_pendentes_sem_prazo(colecao), valor_padrao=[]) or []


def buscar_pendencias_pendentes_varias_colecoes(colecoes: list[str]) -> dict[str, list[dict[str, Any]]]:
    """
    Mesmo princípio de core/market_data.py::buscar_historicos_precos_em_paralelo
    e core/b3_publico.py::buscar_proventos_anunciados_varios (2026-09-04):
    busca várias coleções de pendências do celular AO MESMO TEMPO em vez de
    uma de cada vez — `atualizar_dados` (ui/acoes_comuns.py) precisa
    consultar 4 coleções (compras, remoções, preço-teto, teses) logo no
    início, e fazer isso em sequência (mesmo já com cada uma limitada a
    TIMEOUT_TOTAL_OPERACAO_FIRESTORE_SEGUNDOS) ainda somava até 4x esse
    prazo. Cada busca individual já é protegida por buscar_pendencias_pendentes
    (prazo total + nunca lança exceção), então rodar em paralelo aqui é
    seguro — nenhuma tem efeito colateral, é só leitura.

    Devolve um dict {coleção: lista de pendências} com uma entrada para
    CADA coleção pedida (lista vazia se não achou nada ou se demorou
    demais) — quem chama nunca precisa checar se a chave existe.
    """
    resultado: dict[str, list[dict[str, Any]]] = {}
    if not colecoes:
        return resultado
    with ThreadPoolExecutor(max_workers=len(colecoes)) as executor:
        futuro_por_colecao = {executor.submit(buscar_pendencias_pendentes, colecao): colecao for colecao in colecoes}
        for futuro in as_completed(futuro_por_colecao):
            colecao = futuro_por_colecao[futuro]
            try:
                resultado[colecao] = futuro.result()
            except Exception:
                resultado[colecao] = []
    return resultado


def _marcar_pendencia_sem_prazo(
    doc_id: str, status: str, mensagem_erro: str | None, colecao: str, campos_extra: dict[str, Any] | None
) -> None:
    """Faz o trabalho de verdade de marcar_pendencia() — separado para poder rodar dentro do prazo rígido de _rodar_com_prazo_total."""
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
        db.collection(colecao).document(doc_id).update(atualizacao, timeout=TIMEOUT_FIRESTORE_SEGUNDOS)
    except Exception:
        pass


def marcar_pendencia(
    doc_id: str, status: str, mensagem_erro: str | None = None,
    colecao: str = COLECAO_PENDENCIAS, campos_extra: dict[str, Any] | None = None,
) -> None:
    """Atualiza o status de um pedido do celular (aplicado/erro) depois de processá-lo,
    opcionalmente gravando campos extra no mesmo documento (ex: o resultado calculado
    da calculadora de preço teto, pra o celular exibir sem precisar de outra consulta).
    Nunca trava nem lança exceção — se falhar ou demorar demais (2026-09-04, ver
    _rodar_com_prazo_total), o pior caso é o celular continuar mostrando
    "pendente" um pouco mais, sem travar o app do PC."""
    _rodar_com_prazo_total(
        lambda: _marcar_pendencia_sem_prazo(doc_id, status, mensagem_erro, colecao, campos_extra), valor_padrao=None
    )
