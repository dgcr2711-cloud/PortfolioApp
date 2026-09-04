import React, { useState } from 'react';
import { ActivityIndicator, Alert, FlatList, ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { addDoc, collection, doc, onSnapshot, serverTimestamp } from 'firebase/firestore';
import { db } from '../firebase';
import { usePortfolioSnapshot } from '../hooks/usePortfolioSnapshot';
import { cores, espacamento } from '../theme';
import { formatarData, formatarMoeda } from '../format';
import type { Transacao } from '../types';

/**
 * Espelha a tabela "Histórico de Transações" da aba 🧾 Compras & Vendas do
 * PC — só leitura, os dados vêm prontos do snapshot. O botão de remover
 * segue o MESMO padrão de "pedido pendente" da Nova Compra: cria um
 * documento em pendencias_remocoes, e só quando o app do PC estiver aberto
 * e você clicar em "🔄 Atualizar Dados" a transação é removida de verdade
 * (igual clicar em "🗑️ Remover uma transação" lá).
 *
 * 2026-09-04 (Diego pediu "filtro pro histórico de compras, ação por
 * ação" — mesmo pedido aplicado no PC, `ui/compras.py::_tabela_transacoes`):
 * chips horizontais roláveis (um por ticker + "Todos") em vez de um
 * `SegmentedControl` — o mesmo motivo da correção da aba "Mais": um
 * controle de abas numa linha só quebra com muitos ativos, um carrossel
 * horizontal escala bem com qualquer quantidade de tickers.
 */
const COLECAO_PENDENCIAS_REMOCOES = 'pendencias_remocoes';

type StatusRemocao = 'idle' | 'enviando' | 'pendente' | 'aplicado' | 'erro';

export function HistoricoScreen() {
  const { snapshot, carregando, erro } = usePortfolioSnapshot();
  const [statusPorId, setStatusPorId] = useState<Record<string, StatusRemocao>>({});
  const [mensagemErroPorId, setMensagemErroPorId] = useState<Record<string, string>>({});
  const [tickerFiltro, setTickerFiltro] = useState<string | null>(null);

  async function pedirRemocao(transacao: Transacao) {
    setStatusPorId((anterior) => ({ ...anterior, [transacao.id]: 'enviando' }));
    try {
      const referencia = await addDoc(collection(db, COLECAO_PENDENCIAS_REMOCOES), {
        compraId: transacao.id,
        criadoEm: serverTimestamp(),
        status: 'pendente',
      });
      setStatusPorId((anterior) => ({ ...anterior, [transacao.id]: 'pendente' }));

      const cancelarInscricao = onSnapshot(doc(db, COLECAO_PENDENCIAS_REMOCOES, referencia.id), (snap) => {
        const dadosDoc = snap.data();
        if (!dadosDoc) return;
        if (dadosDoc.status === 'aplicado') {
          setStatusPorId((anterior) => ({ ...anterior, [transacao.id]: 'aplicado' }));
          cancelarInscricao();
        } else if (dadosDoc.status === 'erro') {
          setStatusPorId((anterior) => ({ ...anterior, [transacao.id]: 'erro' }));
          setMensagemErroPorId((anterior) => ({ ...anterior, [transacao.id]: dadosDoc.mensagemErro ?? 'Não foi possível remover.' }));
          cancelarInscricao();
        }
      });
    } catch {
      setStatusPorId((anterior) => ({ ...anterior, [transacao.id]: 'erro' }));
      setMensagemErroPorId((anterior) => ({ ...anterior, [transacao.id]: 'Falha ao enviar. Confira sua conexão com a internet.' }));
    }
  }

  function confirmarRemocao(transacao: Transacao) {
    Alert.alert(
      'Remover transação',
      `${transacao.tipo === 'venda' ? 'Venda' : 'Compra'} de ${transacao.qtd}x ${transacao.ticker} em ${formatarData(transacao.data)}. Isso será aplicado na próxima vez que o app do PC atualizar os dados.`,
      [
        { text: 'Cancelar', style: 'cancel' },
        { text: 'Remover', style: 'destructive', onPress: () => pedirRemocao(transacao) },
      ]
    );
  }

  if (carregando) {
    return (
      <View style={estilos.centralizado}>
        <ActivityIndicator color={cores.destaque} size="large" />
      </View>
    );
  }

  if (erro || !snapshot) {
    return (
      <View style={estilos.centralizado}>
        <Text style={estilos.textoErro}>{erro ?? 'Sem dados.'}</Text>
      </View>
    );
  }

  const todasTransacoes = snapshot.compras ?? [];
  const tickers = Array.from(new Set(todasTransacoes.map((t: Transacao) => t.ticker))).sort();
  const transacoesFiltradas = tickerFiltro ? todasTransacoes.filter((t: Transacao) => t.ticker === tickerFiltro) : todasTransacoes;

  return (
    <FlatList
      style={estilos.container}
      contentContainerStyle={estilos.lista}
      data={transacoesFiltradas}
      keyExtractor={(item: Transacao) => item.id}
      ListHeaderComponent={
        <>
          <Text style={estilos.titulo}>Histórico</Text>
          <Text style={estilos.legenda}>Todas as compras e vendas registradas — a remoção só é aplicada quando o PC sincronizar.</Text>
          {tickers.length > 0 && (
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={estilos.filtroContainer}
              style={estilos.filtroScroll}
            >
              <ChipFiltro rotulo="Todos" ativo={tickerFiltro === null} onPress={() => setTickerFiltro(null)} />
              {tickers.map((ticker: string) => (
                <ChipFiltro key={ticker} rotulo={ticker} ativo={tickerFiltro === ticker} onPress={() => setTickerFiltro(ticker)} />
              ))}
            </ScrollView>
          )}
        </>
      }
      ListEmptyComponent={
        <Text style={estilos.aviso}>
          {tickerFiltro ? `Nenhuma transação de ${tickerFiltro} encontrada.` : 'Nenhuma transação registrada ainda.'}
        </Text>
      }
      renderItem={({ item }: { item: Transacao }) => (
        <LinhaTransacao
          transacao={item}
          status={statusPorId[item.id] ?? 'idle'}
          mensagemErro={mensagemErroPorId[item.id]}
          onRemover={() => confirmarRemocao(item)}
        />
      )}
    />
  );
}

function ChipFiltro({ rotulo, ativo, onPress }: { rotulo: string; ativo: boolean; onPress: () => void }) {
  return (
    <TouchableOpacity
      style={[estilos.chip, ativo && estilos.chipAtivo]}
      onPress={onPress}
      activeOpacity={0.7}
    >
      <Text style={[estilos.textoChip, ativo && estilos.textoChipAtivo]}>{rotulo}</Text>
    </TouchableOpacity>
  );
}

function LinhaTransacao({
  transacao,
  status,
  mensagemErro,
  onRemover,
}: {
  transacao: Transacao;
  status: StatusRemocao;
  mensagemErro: string | undefined;
  onRemover: () => void;
}) {
  const total = transacao.tipo === 'venda'
    ? transacao.qtd * transacao.preco - transacao.taxas
    : transacao.qtd * transacao.preco + transacao.taxas;

  return (
    <View style={estilos.cartao}>
      <View style={estilos.linhaTopo}>
        <Text style={estilos.ticker}>
          {transacao.tipo === 'venda' ? '🔴' : '🟢'} {transacao.ticker}
        </Text>
        <Text style={estilos.data}>{formatarData(transacao.data)}</Text>
      </View>
      <View style={estilos.linhaDetalhe}>
        <Text style={estilos.detalhe}>{transacao.qtd}x {formatarMoeda(transacao.preco)}</Text>
        <Text style={estilos.total}>{formatarMoeda(total)}</Text>
      </View>

      {status === 'idle' && (
        <TouchableOpacity style={estilos.botaoRemover} onPress={onRemover}>
          <Text style={estilos.textoBotaoRemover}>🗑️ Remover</Text>
        </TouchableOpacity>
      )}
      {status === 'enviando' && <ActivityIndicator style={estilos.espacoStatus} color={cores.destaque} size="small" />}
      {status === 'pendente' && <Text style={[estilos.textoStatus, estilos.espacoStatus]}>⏳ Pedido enviado — aguardando o PC sincronizar.</Text>}
      {status === 'aplicado' && <Text style={[estilos.textoStatus, estilos.espacoStatus, { color: cores.positivo }]}>✅ Removida.</Text>}
      {status === 'erro' && <Text style={[estilos.textoStatus, estilos.espacoStatus, { color: cores.negativo }]}>⚠️ {mensagemErro}</Text>}
    </View>
  );
}

const estilos = StyleSheet.create({
  container: { flex: 1, backgroundColor: cores.fundoApp },
  centralizado: { flex: 1, backgroundColor: cores.fundoApp, alignItems: 'center', justifyContent: 'center', padding: espacamento.xl },
  textoErro: { color: cores.textoSecundario, textAlign: 'center', fontSize: 14 },
  lista: { paddingHorizontal: espacamento.lg, paddingTop: espacamento.xl, paddingBottom: espacamento.xl },
  titulo: { color: cores.texto, fontSize: 26, fontWeight: '700' },
  legenda: { color: cores.textoApagado, fontSize: 12, marginTop: 2, marginBottom: espacamento.lg, lineHeight: 17 },
  aviso: { color: cores.neutro, fontSize: 13, lineHeight: 19 },
  filtroScroll: { marginBottom: espacamento.md },
  filtroContainer: { gap: espacamento.sm, paddingRight: espacamento.lg },
  chip: {
    paddingVertical: 6,
    paddingHorizontal: espacamento.md,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: cores.borda,
    backgroundColor: cores.fundoCard,
  },
  chipAtivo: { backgroundColor: 'rgba(212,175,55,0.16)', borderColor: cores.destaque },
  textoChip: { color: cores.textoSecundario, fontSize: 13, fontWeight: '600' },
  textoChipAtivo: { color: cores.destaque },
  cartao: {
    backgroundColor: cores.fundoCard,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: cores.borda,
    padding: espacamento.md,
    marginBottom: espacamento.sm,
  },
  linhaTopo: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  ticker: { color: cores.texto, fontSize: 15, fontWeight: '700' },
  data: { color: cores.textoSecundario, fontSize: 12 },
  linhaDetalhe: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 6 },
  detalhe: { color: cores.textoSecundario, fontSize: 12 },
  total: { color: cores.texto, fontSize: 13, fontWeight: '600' },
  botaoRemover: { marginTop: espacamento.sm, alignSelf: 'flex-start' },
  textoBotaoRemover: { color: cores.negativo, fontSize: 12, fontWeight: '600' },
  espacoStatus: { marginTop: espacamento.sm, alignSelf: 'flex-start' },
  textoStatus: { color: cores.textoSecundario, fontSize: 11, lineHeight: 16 },
});
