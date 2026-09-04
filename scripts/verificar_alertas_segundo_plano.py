"""
Script de atualização completa em SEGUNDO PLANO (2026-08-30, canal WhatsApp
desde 2026-08-31; ampliado 2026-09-05 para fazer TUDO que o botão
"🔄 Atualizar Dados" do PC faz, não só verificar alertas — é o que elimina a
dependência do PC estar ligado para o celular continuar sincronizando).

Roda sozinho, num horário fixo, mesmo que o PC esteja desligado e ninguém
abra o app naquele dia — pelo GitHub Actions (ver
.github/workflows/verificar_alertas.yml para o agendamento). Faz, em ordem,
exatamente o que ui/acoes_comuns.py::atualizar_dados faz no PC — este script
é a versão "sem tela" da mesma lógica, reaproveitando as MESMAS funções core
já testadas, para nunca existir uma segunda implementação que possa divergir:

  1. Aplica pedidos pendentes feitos pelo celular (nova compra/venda,
     remoção de transação, cálculo de preço teto, entrada no diário de
     tese) — core/pendencias_celular.py.
  2. Busca cotações novas no Yahoo Finance (plano B: HG Brasil) para as
     posições e a watchlist, e a cotação do Ibovespa.
  3. Busca proventos anunciados pela B3 (autolimitado a 1x/dia, igual ao
     comportamento do botão no PC).
  4. Registra um snapshot de patrimônio para o gráfico de Evolução.
  5. Compara com os alertas de preço-alvo configurados e manda uma
     mensagem de WhatsApp para os que acabaram de ser atingidos.
  6. Salva tudo — local (disco efêmero do GitHub Actions, sem efeito real)
     e no Firestore, que é o que o PC e o celular realmente leem.
  7. Monta e envia o retrato resumido da carteira (snapshot) pro Firestore,
     pro app do celular ler em tempo real.

Onde ficam as credenciais aqui? Este script roda numa máquina do GitHub, não
no seu PC — não existe a pasta pessoal (~/.portfolio_b3_secrets) nem um app
Streamlit de verdade rodando. Por isso a chave do Firebase e a configuração
do WhatsApp vêm de "Secrets" do próprio repositório do GitHub (Settings ->
Secrets and variables -> Actions), expostos a este script como variáveis de
ambiente — ver core/cloud_sync.py::_obter_credenciais_dict_da_variavel_de_
ambiente e core/notificacoes_whatsapp.py::_carregar_config_da_variavel_de_
ambiente. Nunca ficam no código nem são commitados.

Nunca lança exceção "para cima": qualquer problema (sem cotação para um
ticker, Firestore fora do ar, CallMeBot fora do ar, site da B3 bloqueando
etc.) já é tratado dentro das próprias funções reaproveitadas aqui (mesmas
usadas e testadas no app principal) — este script só decide o que imprimir
no log do GitHub Actions e qual código de saída devolver.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# 2026-09-05 — dois ajustes que precisam vir ANTES de qualquer outro import
# (inclusive antes de "from core import ..." logo abaixo, porque cloud_sync
# importa firebase_admin/grpc por dentro de função, na primeira vez que for
# chamada — o que já acontece já na primeira linha de main()):
#
# 1) Log SEM buffer: por padrão, quando a saída não é um terminal de verdade
#    (exatamente o caso do GitHub Actions, que captura a saída por um pipe),
#    o Python usa buffer "de bloco" pro stdout — várias linhas de print()
#    só aparecem de uma vez, muito depois de terem realmente acontecido, com
#    o MESMO horário registrado no log pra todas. Foi isso que fez um log
#    real (baixado em 2026-09-04) mostrar 6 prints diferentes — desde
#    "Firebase inicializado com sucesso" até "Falha ao salvar... Firestore"
#    — todos no mesmíssimo milissegundo, escondendo COMPLETAMENTE quanto
#    tempo cada etapa levou de verdade. Sem isso corrigido, é impossível
#    diagnosticar onde o tempo (e uma eventual trava) está acontecendo.
try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except (AttributeError, ValueError, OSError):
    # 2026-09-05 — descoberto testando de verdade (não só no GitHub Actions:
    # também rodando com a saída redirecionada, como um teste automatizado
    # faz): nem todo objeto que se comporta como stdout/stderr tem
    # `.reconfigure()` (ex: um StringIO usado por um teste). Isto aqui é só
    # uma melhoria de diagnóstico (ver comentário abaixo) — nunca pode ser o
    # motivo de o script inteiro travar antes mesmo de começar a atualizar
    # os dados de verdade.
    pass

# 2) DNS "nativo" pro gRPC: a biblioteca do Firebase/Firestore fala com o
#    Google por gRPC, que por padrão usa seu PRÓPRIO resolvedor de DNS
#    (c-ares), em vez do resolvedor do sistema operacional — e esse
#    resolvedor embutido tem um histórico bem documentado (issues abertas
#    nos repositórios oficiais googleapis/google-cloud-python e
#    grpc/grpc) de ficar preso por dezenas de segundos, ou falhar
#    silenciosamente, especificamente dentro de containers Linux
#    restritos/sandboxed — exatamente o ambiente de uma runner do GitHub
#    Actions. Isso bate com dois sintomas vistos no log real: (a) uma pausa
#    de ~62s sem NENHUMA saída logo antes do diagnóstico do Firebase
#    aparecer, e (b) a escrita no Firestore falhando com
#    "RetryError('Timeout of 60.0s exceeded')" mesmo com um `timeout=` bem
#    menor (10s) passado direto pra chamada — porque esse `timeout=` só
#    limita CADA tentativa individual; o prazo TOTAL de 60s pra desistir de
#    tentar de novo é um padrão interno da própria biblioteca do Google,
#    que só é atingido se as tentativas individuais estiverem MESMO
#    falhando (ex: por causa desse DNS travando/errando). Forçar o
#    resolvedor nativo do sistema operacional (que a runner do GitHub já
#    sabe resolver DNS sem problema, como qualquer navegador comum) é a
#    correção padrão recomendada pelo próprio Google pra esse exato quadro
#    de sintomas — precisa estar definida ANTES da primeira vez que o gRPC
#    é carregado (por isso aqui em cima, antes de qualquer outro import).
os.environ.setdefault("GRPC_DNS_RESOLVER", "native")

# 3) O FILTRO do aviso do Streamlit ("No runtime found, using
#    MemoryCacheStorageManager") precisa ficar AQUI EM CIMA também — não
#    logo abaixo dos imports de "core"/"ui" como estava antes. Motivo,
#    descoberto só agora lendo o log real com timestamp por linha
#    (2026-09-05, depois do ajuste (1) acima): o aviso aparece ANTES até do
#    diagnóstico da credencial do Firebase, que é a primeira linha de
#    main() — ou seja, ele dispara durante a IMPORTAÇÃO dos módulos
#    (core/market_data.py e core/fundamentals.py têm funções decoradas com
#    @st.cache_data, e o Streamlit já verifica "existe uma tela rodando?"
#    no momento em que decora a função, não só quando ela é chamada). Como
#    o filtro só era anexado DEPOIS de "from core import ...", ele sempre
#    chegava tarde demais — o aviso já tinha sido logado. Continuava
#    aparecendo em todo log mesmo com o filtro presente no arquivo. Um
#    teste automatizado anterior (com um Streamlit falso/stub) não pegou
#    esse problema porque o stub não reproduzia esse detalhe exato do
#    Streamlit de verdade — reforça por que testar com o log real, não só
#    com stub, importa.
#
# Por que um Filter, e não logger.setLevel(): já tentei setLevel (antes E
# depois dos imports) e o aviso continuou aparecendo — o Streamlit
# reconfigura o nível desse logger por conta própria toda vez que emite o
# aviso (não só uma vez, na importação), então qualquer setLevel externo é
# sobrescrito de novo na próxima chamada. Testei isso isoladamente (mesmo
# simulando esse comportamento "teimoso") e confirmei: um logging.Filter
# anexado direto no logger sobrevive a isso, porque é checado depois que a
# lib decide logar, não depende do nível dela ficar como eu quero.
logging.getLogger("streamlit.runtime.caching.cache_data_api").addFilter(lambda registro: False)

# Permite rodar este script diretamente (python scripts/verificar_alertas_segundo_plano.py)
# sem precisar instalar o projeto como pacote — mesmo truque usado em app.py.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import b3_publico, calculations as calc, cloud_sync, market_data  # noqa: E402
from core.config import INTERVALO_ATUALIZACAO_PROVENTOS_B3_SEGUNDOS  # noqa: E402
from core.data_store import carregar_dados, salvar_dados  # noqa: E402
from core.mobile_snapshot import montar_snapshot_para_celular  # noqa: E402
from core.notificacoes_whatsapp import (  # noqa: E402
    notificacoes_configuradas,
    verificar_e_notificar_alertas,
)
from core.pendencias_celular import (  # noqa: E402
    aplicar_calculos_teto_do_celular,
    aplicar_pendencias_do_celular,
    aplicar_remocoes_do_celular,
    aplicar_teses_do_celular,
)
from ui.acoes_comuns import _registrar_snapshot  # noqa: E402

# 2026-09-05 — aumenta SÓ NESTE SCRIPT (nunca no app do PC, onde alguém
# está esperando na tela — por isso 12s ali, de propósito, ver comentário
# em core/cloud_sync.py) o prazo total que cada chamada ao Firestore pode
# demorar antes de desistir. Motivo: rodando no GitHub Actions, uma
# gravação chegou a falhar com "RetryError('Timeout of 60.0s exceeded')" —
# ou seja, a própria biblioteca do Google já esperava até 60s por conta
# própria, só que nosso prazo de 12s desistia (e "abandonava" a tentativa
# numa thread órfã) bem antes disso, escondendo o resultado real. Aqui
# ninguém está olhando pra tela esperando, então não custa nada esperar o
# tempo que o Google realmente precisa (60s) mais uma margem de segurança.
cloud_sync.TIMEOUT_TOTAL_CARREGAR_NUVEM_SEGUNDOS = 70
cloud_sync.TIMEOUT_TOTAL_OPERACAO_FIRESTORE_SEGUNDOS = 70


def _atualizar_proventos_b3_sem_tela(dados: dict, forcar: bool = False) -> None:
    """
    Mesma lógica de ui/acoes_comuns.py::atualizar_proventos_b3, sem as
    chamadas a st.spinner/st.session_state (que exigem um app Streamlit de
    verdade rodando — travariam este script). Só altera `dados` em memória;
    quem chama salva depois (este script salva tudo de uma vez só, no
    final, em vez de a cada etapa como o botão do PC faz).
    """
    agora = datetime.now()
    if not forcar and not b3_publico.precisa_atualizar(
        dados.get("proventosAnunciadosB3AtualizadoEm"), agora, INTERVALO_ATUALIZACAO_PROVENTOS_B3_SEGUNDOS
    ):
        return

    posicoes = calc.consolidar_posicoes(dados["compras"], dados["eventos"])
    tickers_posicoes = {p["ticker"] for p in posicoes}
    tickers_alvo = [t for t in dados["watchlist"] if t not in tickers_posicoes]
    tickers = [p["ticker"] for p in posicoes] + tickers_alvo
    if not tickers:
        return

    anunciados, sem_conexao = b3_publico.buscar_proventos_anunciados_varios(tickers)
    if sem_conexao:
        print("[atualizar] Aviso: não consegui acessar o site da B3 agora — tento de novo na próxima execução.")
        return

    dados["proventosAnunciadosB3"] = anunciados
    dados["proventosAnunciadosB3AtualizadoEm"] = agora.isoformat()
    print(f"[atualizar] Proventos anunciados pela B3 atualizados para {len(anunciados)} ativo(s).")


def _diagnosticar_credencial_firebase() -> None:
    """
    Diagnóstico TEMPORÁRIO (2026-09-04): a leitura E a escrita no Firestore
    estão falhando silenciosamente neste script rodando no GitHub Actions
    (a carteira sempre volta com a watchlist padrão de conta vazia — nunca
    os dados reais), o que só é possível se a conexão com o Firebase nunca
    chegar a se estabelecer aqui. Isto imprime só METADADOS sobre o Secret
    (existe? tamanho? é um JSON válido? tem os campos esperados?) — NUNCA o
    conteúdo da chave em si — e tenta inicializar o Firebase isoladamente
    pra capturar a exceção real, que hoje fica escondida porque
    _garantir_firebase_inicializado() não é chamada dentro de nenhum
    try/except nos pontos onde é usada.
    """
    bruto = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
    if not bruto:
        print("[diagnostico] FIREBASE_SERVICE_ACCOUNT_JSON: variável de ambiente AUSENTE ou vazia neste job.")
        return
    print(f"[diagnostico] FIREBASE_SERVICE_ACCOUNT_JSON: presente, {len(bruto)} caracteres.")
    try:
        credenciais = json.loads(bruto)
    except json.JSONDecodeError as erro:
        print(f"[diagnostico] FIREBASE_SERVICE_ACCOUNT_JSON não é um JSON válido: {erro}")
        return
    if not isinstance(credenciais, dict):
        print(f"[diagnostico] FIREBASE_SERVICE_ACCOUNT_JSON é um JSON válido, mas do tipo {type(credenciais).__name__}, não um objeto.")
        return
    campos_esperados = ["type", "project_id", "private_key_id", "private_key", "client_email"]
    faltando = [campo for campo in campos_esperados if campo not in credenciais]
    print(f"[diagnostico] JSON válido, chaves presentes: {sorted(credenciais.keys())}.")
    if faltando:
        print(f"[diagnostico] Faltando campo(s) esperado(s) de uma chave de conta de serviço: {faltando}.")

    try:
        import firebase_admin
        from firebase_admin import credentials

        if not firebase_admin._apps:
            cred = credentials.Certificate(credenciais)
            firebase_admin.initialize_app(cred)
        print("[diagnostico] Firebase inicializado com sucesso a partir da variável de ambiente.")
    except Exception as erro:
        print(f"[diagnostico] Falha ao inicializar o Firebase com essa credencial: {erro!r}")


def main() -> int:
    _diagnosticar_credencial_firebase()
    dados = carregar_dados()

    # 1. Pedidos pendentes do celular — mesma busca em paralelo já usada
    # pelo botão do PC (ver core/cloud_sync.py::buscar_pendencias_pendentes_varias_colecoes).
    pendencias_por_colecao = cloud_sync.buscar_pendencias_pendentes_varias_colecoes([
        cloud_sync.COLECAO_PENDENCIAS,
        cloud_sync.COLECAO_PENDENCIAS_REMOCOES,
        cloud_sync.COLECAO_PENDENCIAS_PRECO_TETO,
        cloud_sync.COLECAO_PENDENCIAS_TESE,
    ])
    aplicadas, erros_compra = aplicar_pendencias_do_celular(
        dados, salvar_dados, pendencias_por_colecao.get(cloud_sync.COLECAO_PENDENCIAS)
    )
    removidas, erros_remocao = aplicar_remocoes_do_celular(
        dados, salvar_dados, pendencias_por_colecao.get(cloud_sync.COLECAO_PENDENCIAS_REMOCOES)
    )
    calculadas, erros_calculo = aplicar_calculos_teto_do_celular(
        dados, salvar_dados, pendencias_por_colecao.get(cloud_sync.COLECAO_PENDENCIAS_PRECO_TETO)
    )
    teses_aplicadas, erros_tese = aplicar_teses_do_celular(
        dados, salvar_dados, pendencias_por_colecao.get(cloud_sync.COLECAO_PENDENCIAS_TESE)
    )
    total_celular = aplicadas + removidas + calculadas + teses_aplicadas
    total_erros_celular = erros_compra + erros_remocao + erros_calculo + erros_tese
    if total_celular:
        print(
            f"[atualizar] {total_celular} pedido(s) do celular aplicado(s) "
            f"({aplicadas} compra/venda, {removidas} remoção(ões), {calculadas} preço(s) teto, {teses_aplicadas} tese(s))."
        )
    if total_erros_celular:
        print(f"[atualizar] Aviso: {total_erros_celular} pedido(s) do celular não puderam ser aplicados (dados inválidos).")

    # 2. Cotações.
    posicoes = calc.consolidar_posicoes(dados["compras"], dados["eventos"])
    tickers_posicoes = {p["ticker"] for p in posicoes}
    tickers_alvo = [t for t in dados["watchlist"] if t not in tickers_posicoes]
    tickers = [p["ticker"] for p in posicoes] + tickers_alvo

    if not tickers:
        print("[atualizar] Nenhuma posição nem empresa-alvo na carteira — nada a atualizar.")
        salvar_dados(dados)
        return 0

    print(f"[atualizar] Buscando cotação de {len(tickers)} ativo(s) no Yahoo Finance...")
    novas_cotacoes, falhas = market_data.atualizar_cotacoes(tickers, dados["cotacoes"])
    dados["cotacoes"] = novas_cotacoes
    ibov = market_data.buscar_cotacao_ibovespa()

    if falhas:
        cotacoes_hgbrasil = market_data.buscar_cotacoes_hgbrasil(falhas)
        for ticker, cotacao in cotacoes_hgbrasil.items():
            dados["cotacoes"][ticker] = cotacao
        falhas = [t for t in falhas if t not in cotacoes_hgbrasil]
        if falhas:
            print(f"[atualizar] Aviso: sem cotação para {', '.join(falhas)} nesta tentativa.")

    taxas_economicas = market_data.buscar_taxas_economicas()
    if taxas_economicas is not None:
        dados["taxasEconomicas"] = taxas_economicas

    # 3. Proventos anunciados pela B3 (autolimitado a 1x/dia).
    _atualizar_proventos_b3_sem_tela(dados)

    # 4. Snapshot de patrimônio para o gráfico de Evolução.
    _registrar_snapshot(dados, ibov)

    # 5. Alertas de preço-alvo por WhatsApp.
    enviados = 0
    if notificacoes_configuradas() and dados.get("alertas"):
        tickers_atualizados = [t for t in tickers if t not in falhas]
        cotacao_por_ticker = {
            t: dados["cotacoes"][t]["preco"] for t in tickers_atualizados if t in dados["cotacoes"]
        }
        enviados = verificar_e_notificar_alertas(dados, cotacao_por_ticker)
        if enviados:
            plural = "s" if enviados > 1 else ""
            print(f"[atualizar] {enviados} alerta{plural} de preço enviado{plural} por WhatsApp.")

    # 6. Salva tudo — local (efêmero, sem efeito real neste ambiente) e no
    # Firestore, que é o que o PC e o celular realmente leem.
    salvar_dados(dados)

    # 7. Snapshot resumido pro celular ler em tempo real.
    #
    # IMPORTANTE (2026-09-04): NÃO usa cloud_sync.sincronizacao_configurada()
    # como guarda aqui — essa função só olha se existe um ARQUIVO de chave
    # local (~/.portfolio_b3_secrets), o que nunca é verdade rodando no
    # GitHub Actions (aqui a chave vem da variável de ambiente
    # FIREBASE_SERVICE_ACCOUNT_JSON). Usá-la como guarda fazia este bloco
    # inteiro ser pulado em silêncio nesse ambiente — a sincronização com o
    # celular nunca rodava, mesmo com a chave certa configurada no Secret do
    # repositório. cloud_sync.sincronizar_snapshot() já sabe lidar sozinho
    # com "não configurado" (devolve False sem erro), então chama direto.
    sincronizado = cloud_sync.sincronizar_snapshot(montar_snapshot_para_celular(dados))
    status = "ok" if sincronizado else "falhou ou não configurada (sem internet, chave inválida ou Secret ausente)"
    print(f"[atualizar] Sincronização com o celular: {status}.")

    print("[atualizar] Execução concluída com sucesso.")
    return 0


if __name__ == "__main__":
    _codigo_saida = main()

    # 2026-09-05 — a execução real terminou aqui (tudo já foi salvo antes
    # disso), mas um `raise SystemExit(...)` normal ESPERA todas as threads
    # não-daemon do processo terminarem sozinhas antes de sair de verdade —
    # e a biblioteca de rede do Google (gRPC, usada por trás do Firestore)
    # mantém suas próprias threads internas de gerenciamento de conexão
    # rodando em segundo plano, que não são daemon e podem demorar MINUTOS
    # pra encerrar sozinhas. Foi exatamente isso que fez uma execução real
    # (2026-09-04) aparecer com "4m 42s" de duração no GitHub Actions mesmo
    # com "[atualizar] Execução concluída com sucesso." já impresso — o
    # trabalho de verdade tinha acabado em segundos; o resto do tempo foi só
    # esperando essas threads internas do gRPC. `os._exit()` encerra o
    # processo imediatamente, sem esperar nenhuma thread — seguro aqui
    # porque não há nada pendente pra terminar (nenhum arquivo aberto pra
    # fechar, nenhuma escrita pendente: tudo já foi salvo em main() antes de
    # chegar neste ponto). Os flushes abaixo garantem que a última linha
    # impressa não fique presa no buffer sem nunca aparecer no log.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(_codigo_saida)
