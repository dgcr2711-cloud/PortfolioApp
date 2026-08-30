import React, { useMemo, useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { addDoc, collection, doc, onSnapshot, serverTimestamp } from 'firebase/firestore';
import { db } from '../firebase';
import { usePortfolioSnapshot } from '../hooks/usePortfolioSnapshot';
import { cores, espacamento } from '../theme';
import { Badge } from '../components/Badge';

/**
 * Diário de Tese de Investimento, no celular — mesma ideia da aba
 * "📓 Diário de Tese" do PC: por que você comprou (ou está de olho em)
 * cada ativo, pra reler mais tarde.
 *
 * O histórico (abaixo) vem do retrato normal da carteira (snapshot), lido
 * em tempo real — mesmo texto que já está salvo no PC. Escrever uma
 * entrada NOVA funciona como o resto do celular: cria um "pedido
 * pendente" no Firestore (pendencias_teses); só entra de verdade no
 * diário quando o app do PC abrir e sincronizar (core/pendencias_celular.py).
 */
const COLECAO_PENDENCIAS = 'pendencias_teses';
const LIMITE_CARACTERES = 4000;

type StatusEnvio = 'idle' | 'enviando' | 'pendente' | 'aplicado' | 'erro';

export function TeseScreen() {
  const { snapshot, carregando, erro: erroSnapshot } = usePortfolioSnapshot();

  const tickers = useMemo(() => {
    if (!snapshot) return [];
    return [...snapshot.ativos.map((a) => a.ticker)].sort();
  }, [snapshot]);

  const [tickerSelecionado, setTickerSelecionado] = useState<string | null>(null);
  const [textoNovo, setTextoNovo] = useState('');
  const [status, setStatus] = useState<StatusEnvio>('idle');
  const [mensagemErro, setMensagemErro] = useState<string | null>(null);

  const ticker = tickerSelecionado ?? tickers[0] ?? null;
  const entradas = ticker && snapshot?.teses ? snapshot.teses[ticker] ?? [] : [];

  async function enviar() {
    if (!ticker) return;
    const texto = textoNovo.trim();
    if (!texto) return;

    setStatus('enviando');
    setMensagemErro(null);

    try {
      const referencia = await addDoc(collection(db, COLECAO_PENDENCIAS), {
        ticker,
        texto,
        criadoEm: serverTimestamp(),
        status: 'pendente',
      });
      setStatus('pendente');

      const cancelarInscricao = onSnapshot(doc(db, COLECAO_PENDENCIAS, referencia.id), (snap) => {
        const dadosDoc = snap.data();
        if (!dadosDoc) return;
        if (dadosDoc.status === 'aplicado') {
          setStatus('aplicado');
          setTextoNovo('');
          cancelarInscricao();
        } else if (dadosDoc.status === 'erro') {
          setStatus('erro');
          setMensagemErro(dadosDoc.mensagemErro ?? 'Não foi possível salvar esta entrada.');
          cancelarInscricao();
        }
      });
    } catch {
      setStatus('erro');
      setMensagemErro('Falha ao enviar. Confira sua conexão com a internet.');
    }
  }

  if (carregando) {
    return (
      <View style={estilos.centro}>
        <ActivityIndicator color={cores.destaque} />
      </View>
    );
  }

  if (erroSnapshot || tickers.length === 0) {
    return (
      <View style={estilos.centro}>
        <Text style={estilos.textoVazio}>
          {erroSnapshot ?? 'Nenhum ativo ainda. Registre uma compra ou empresa-alvo no app do PC primeiro.'}
        </Text>
      </View>
    );
  }

  return (
    <KeyboardAvoidingView style={estilos.container} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView contentContainerStyle={estilos.conteudo} keyboardShouldPersistTaps="handled">
        <Text style={estilos.titulo}>Diário de Tese</Text>
        <Text style={estilos.legenda}>
          Por que você comprou (ou está de olho em) este ativo — pra reler daqui a um tempo. Entradas enviadas
          daqui ficam pendentes até o app do PC abrir e sincronizar.
        </Text>

        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={estilos.linhaTickers}>
          {tickers.map((t) => (
            <TouchableOpacity
              key={t}
              style={[estilos.chipTicker, t === ticker && estilos.chipTickerAtivo]}
              onPress={() => setTickerSelecionado(t)}
            >
              <Text style={[estilos.textoChip, t === ticker && estilos.textoChipAtivo]}>{t}</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>

        <TextInput
          style={estilos.input}
          placeholder="Escreva sua tese para este ativo..."
          placeholderTextColor={cores.textoApagado}
          multiline
          numberOfLines={5}
          maxLength={LIMITE_CARACTERES}
          value={textoNovo}
          onChangeText={setTextoNovo}
        />

        <TouchableOpacity
          style={[estilos.botao, (status === 'enviando' || !textoNovo.trim()) && estilos.botaoDesabilitado]}
          onPress={enviar}
          disabled={status === 'enviando' || !textoNovo.trim()}
        >
          {status === 'enviando' ? (
            <ActivityIndicator color={cores.fundoApp} />
          ) : (
            <Text style={estilos.textoBotao}>💾 Salvar entrada</Text>
          )}
        </TouchableOpacity>

        {status === 'pendente' && (
          <View style={estilos.blocoStatus}>
            <Badge texto="⏳ Pendente" tipo="info" />
            <Text style={estilos.textoStatus}>Enviado! Aguardando o app do PC sincronizar.</Text>
          </View>
        )}
        {status === 'aplicado' && (
          <View style={estilos.blocoStatus}>
            <Badge texto="✅ Salvo" tipo="ok" />
            <Text style={estilos.textoStatus}>Entrada adicionada ao diário.</Text>
          </View>
        )}
        {status === 'erro' && (
          <View style={estilos.blocoStatus}>
            <Badge texto="⚠️ Não salvo" tipo="warn" />
            <Text style={estilos.textoStatus}>{mensagemErro}</Text>
          </View>
        )}

        <Text style={estilos.subtitulo}>Histórico — {ticker}</Text>
        {entradas.length === 0 ? (
          <Text style={estilos.textoVazio}>Nenhuma entrada ainda para {ticker}.</Text>
        ) : (
          entradas.map((entrada) => (
            <View key={entrada.id} style={estilos.cartaoEntrada}>
              <Text style={estilos.dataEntrada}>{formatarDataHora(entrada.data)}</Text>
              <Text style={estilos.textoEntrada}>{entrada.texto}</Text>
            </View>
          ))
        )}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

function formatarDataHora(dataIso: string): string {
  const data = new Date(dataIso);
  if (Number.isNaN(data.getTime())) return dataIso;
  return data.toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}

const estilos = StyleSheet.create({
  container: { flex: 1, backgroundColor: cores.fundoApp },
  centro: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: espacamento.xl },
  conteudo: { padding: espacamento.lg, paddingBottom: espacamento.xl * 2 },
  titulo: { color: cores.texto, fontSize: 22, fontWeight: '700' },
  legenda: { color: cores.textoApagado, fontSize: 12, marginTop: 4, marginBottom: espacamento.md, lineHeight: 17 },
  linhaTickers: { marginBottom: espacamento.md },
  chipTicker: {
    paddingHorizontal: espacamento.md,
    paddingVertical: 8,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: cores.borda,
    marginRight: espacamento.sm,
  },
  chipTickerAtivo: { backgroundColor: 'rgba(212,175,55,0.14)', borderColor: cores.destaque },
  textoChip: { color: cores.textoSecundario, fontWeight: '600', fontSize: 13 },
  textoChipAtivo: { color: cores.destaque },
  input: {
    backgroundColor: cores.fundoCard,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: cores.borda,
    padding: espacamento.md,
    color: cores.texto,
    fontSize: 14,
    minHeight: 110,
    textAlignVertical: 'top',
  },
  botao: {
    backgroundColor: cores.destaque,
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: espacamento.sm,
  },
  botaoDesabilitado: { opacity: 0.6 },
  textoBotao: { color: cores.fundoApp, fontWeight: '700', fontSize: 15 },
  blocoStatus: {
    marginTop: espacamento.lg,
    padding: espacamento.md,
    borderRadius: 10,
    backgroundColor: cores.fundoCard,
    borderWidth: 1,
    borderColor: cores.borda,
    gap: 6,
  },
  textoStatus: { color: cores.textoSecundario, fontSize: 12, lineHeight: 17 },
  subtitulo: { color: cores.texto, fontSize: 16, fontWeight: '600', marginTop: espacamento.xl, marginBottom: espacamento.sm },
  textoVazio: { color: cores.textoApagado, fontSize: 13, textAlign: 'center' },
  cartaoEntrada: {
    backgroundColor: cores.fundoCard,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: cores.borda,
    padding: espacamento.md,
    marginBottom: espacamento.sm,
  },
  dataEntrada: { color: cores.textoApagado, fontSize: 11, marginBottom: 6 },
  textoEntrada: { color: cores.texto, fontSize: 14, lineHeight: 20 },
});
