import React, { useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  FlatList,
  KeyboardAvoidingView,
  Platform,
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
import { formatarMoeda } from '../format';
import type { PrecoTeto } from '../types';

/**
 * Espelha a aba 🎯 Preço Teto do PC: lista dos preços-teto já calculados
 * (só leitura) + a MESMA calculadora de Fluxo de Caixa Descontado (FCD).
 * O cálculo em si continua rodando só no PC (core/calculations.py ->
 * calcular_fcd) — o celular envia as premissas como um "pedido pendente"
 * (pendencias_preco_teto) e mostra o resultado assim que o PC processar,
 * exatamente como a Nova Compra faz. Isso evita reescrever a fórmula
 * financeira em duas linguagens.
 */
const COLECAO_PENDENCIAS_PRECO_TETO = 'pendencias_preco_teto';

type StatusEnvio = 'idle' | 'enviando' | 'pendente' | 'aplicado' | 'erro';

interface ResultadoCalculo {
  precoTeto: number;
  precoTetoComMargem: number;
}

export function PrecoTetoScreen() {
  const { snapshot, carregando, erro } = usePortfolioSnapshot();

  const [ticker, setTicker] = useState('');
  const [fcfBase, setFcfBase] = useState('');
  const [g1, setG1] = useState('');
  const [anos, setAnos] = useState('5');
  const [wacc, setWacc] = useState('');
  const [g2, setG2] = useState('');
  const [divida, setDivida] = useState('0');
  const [nAcoes, setNAcoes] = useState('');
  const [margem, setMargem] = useState('20');

  const [status, setStatus] = useState<StatusEnvio>('idle');
  const [mensagemErro, setMensagemErro] = useState<string | null>(null);
  const [resultado, setResultado] = useState<ResultadoCalculo | null>(null);

  function paraNumero(texto: string): number {
    return Number(texto.replace(',', '.'));
  }

  async function calcular() {
    const tickerLimpo = ticker.trim().toUpperCase();
    if (!tickerLimpo) {
      Alert.alert('Informe o ticker', 'Ex: WEGE3');
      return;
    }
    const nAcoesNumero = paraNumero(nAcoes);
    if (!Number.isFinite(nAcoesNumero) || nAcoesNumero <= 0) {
      Alert.alert('Número de ações inválido', 'Informe um número maior que zero (em milhões).');
      return;
    }
    const anosNumero = paraNumero(anos);
    if (!Number.isFinite(anosNumero) || anosNumero <= 0) {
      Alert.alert('Anos de projeção inválido', 'Informe um número inteiro maior que zero.');
      return;
    }

    setStatus('enviando');
    setMensagemErro(null);
    setResultado(null);

    try {
      const referencia = await addDoc(collection(db, COLECAO_PENDENCIAS_PRECO_TETO), {
        ticker: tickerLimpo,
        fcfBase: paraNumero(fcfBase),
        g1Pct: paraNumero(g1),
        anos: Math.round(anosNumero),
        waccPct: paraNumero(wacc),
        g2Pct: paraNumero(g2),
        dividaLiquida: paraNumero(divida),
        nAcoes: nAcoesNumero,
        margemPct: paraNumero(margem),
        criadoEm: serverTimestamp(),
        status: 'pendente',
      });
      setStatus('pendente');

      const cancelarInscricao = onSnapshot(doc(db, COLECAO_PENDENCIAS_PRECO_TETO, referencia.id), (snap) => {
        const dadosDoc = snap.data();
        if (!dadosDoc) return;
        if (dadosDoc.status === 'aplicado') {
          setStatus('aplicado');
          setResultado({ precoTeto: dadosDoc.precoTeto, precoTetoComMargem: dadosDoc.precoTetoComMargem });
          cancelarInscricao();
        } else if (dadosDoc.status === 'erro') {
          setStatus('erro');
          setMensagemErro(dadosDoc.mensagemErro ?? 'Não foi possível calcular.');
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

  // Fallback pro formato antigo do snapshot (antes desta funcionalidade existir) — evita
  // tela quebrada enquanto o PC ainda não rodou "🔄 Atualizar Dados" com o código novo.
  const precosTeto = snapshot.precosTeto ?? [];

  return (
    <KeyboardAvoidingView style={estilos.container} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <FlatList
        contentContainerStyle={estilos.lista}
        data={precosTeto}
        keyExtractor={(item: PrecoTeto) => item.ticker}
        keyboardShouldPersistTaps="handled"
        ListHeaderComponent={
          <>
            <Text style={estilos.titulo}>Preço Teto</Text>
            <Text style={estilos.legenda}>
              Calculadora de Fluxo de Caixa Descontado (2 estágios). Enviado como pedido — o resultado aparece aqui
              quando o app do PC estiver aberto e sincronizar (e já entra automaticamente na Carteira).
            </Text>

            <Campo rotulo="Ticker">
              <TextInput style={estilos.input} placeholder="Ex: WEGE3" placeholderTextColor={cores.textoApagado} autoCapitalize="characters" maxLength={10} value={ticker} onChangeText={setTicker} />
            </Campo>
            <Campo rotulo="FCF do último ano (R$ milhões)">
              <TextInput style={estilos.input} placeholder="Ex: 1200" placeholderTextColor={cores.textoApagado} keyboardType="decimal-pad" value={fcfBase} onChangeText={setFcfBase} />
            </Campo>
            <View style={estilos.linhaCampos}>
              <Campo rotulo="Cresc. g1 (%)" flex>
                <TextInput style={estilos.input} keyboardType="decimal-pad" value={g1} onChangeText={setG1} />
              </Campo>
              <Campo rotulo="Anos de projeção" flex>
                <TextInput style={estilos.input} keyboardType="number-pad" value={anos} onChangeText={setAnos} />
              </Campo>
            </View>
            <View style={estilos.linhaCampos}>
              <Campo rotulo="WACC (%)" flex>
                <TextInput style={estilos.input} keyboardType="decimal-pad" value={wacc} onChangeText={setWacc} />
              </Campo>
              <Campo rotulo="Cresc. perpetuidade g2 (%)" flex>
                <TextInput style={estilos.input} keyboardType="decimal-pad" value={g2} onChangeText={setG2} />
              </Campo>
            </View>
            <View style={estilos.linhaCampos}>
              <Campo rotulo="Dívida líquida (R$ mi)" flex>
                <TextInput style={estilos.input} keyboardType="decimal-pad" value={divida} onChangeText={setDivida} />
              </Campo>
              <Campo rotulo="Nº ações (milhões)" flex>
                <TextInput style={estilos.input} keyboardType="decimal-pad" value={nAcoes} onChangeText={setNAcoes} />
              </Campo>
            </View>
            <Campo rotulo="Margem de segurança (%)">
              <TextInput style={estilos.input} keyboardType="decimal-pad" value={margem} onChangeText={setMargem} />
            </Campo>

            <TouchableOpacity style={[estilos.botao, status === 'enviando' && estilos.botaoDesabilitado]} onPress={calcular} disabled={status === 'enviando'}>
              {status === 'enviando' ? <ActivityIndicator color={cores.fundoApp} /> : <Text style={estilos.textoBotao}>Calcular Preço Teto</Text>}
            </TouchableOpacity>

            {status === 'pendente' && <Text style={estilos.textoStatus}>⏳ Enviado — aguardando o app do PC sincronizar.</Text>}
            {status === 'aplicado' && resultado && (
              <View style={estilos.blocoResultado}>
                <Text style={[estilos.textoStatus, { color: cores.positivo }]}>✅ Calculado e salvo na Carteira.</Text>
                <View style={estilos.linhaResultado}>
                  <Text style={estilos.rotuloResultado}>Preço Teto</Text>
                  <Text style={estilos.valorResultado}>{formatarMoeda(resultado.precoTeto)}</Text>
                </View>
                <View style={estilos.linhaResultado}>
                  <Text style={estilos.rotuloResultado}>Com margem de segurança</Text>
                  <Text style={estilos.valorResultado}>{formatarMoeda(resultado.precoTetoComMargem)}</Text>
                </View>
              </View>
            )}
            {status === 'erro' && <Text style={[estilos.textoStatus, { color: cores.negativo }]}>⚠️ {mensagemErro}</Text>}

            {precosTeto.length > 0 && <Text style={estilos.subtitulo}>Preços Teto já calculados</Text>}
          </>
        }
        ListEmptyComponent={<Text style={estilos.aviso}>Nenhum preço teto calculado ainda.</Text>}
        renderItem={({ item }: { item: PrecoTeto }) => <LinhaPrecoTeto item={item} />}
      />
    </KeyboardAvoidingView>
  );
}

function LinhaPrecoTeto({ item }: { item: PrecoTeto }) {
  return (
    <View style={estilos.linhaSalva}>
      <View>
        <Text style={estilos.tickerSalvo}>{item.ticker}</Text>
        {item.atualizadoEm && <Text style={estilos.dataSalva}>Calculado em {item.atualizadoEm}</Text>}
      </View>
      <View style={{ alignItems: 'flex-end' }}>
        <Text style={estilos.valorSalvo}>{formatarMoeda(item.precoTeto)}</Text>
        <Text style={estilos.valorSalvoMargem}>c/ margem: {formatarMoeda(item.precoTetoComMargem)}</Text>
      </View>
    </View>
  );
}

function Campo({ rotulo, children, flex = false }: { rotulo: string; children: React.ReactNode; flex?: boolean }) {
  return (
    <View style={[estilos.campo, flex && { flex: 1 }]}>
      <Text style={estilos.rotuloCampo}>{rotulo}</Text>
      {children}
    </View>
  );
}

const estilos = StyleSheet.create({
  container: { flex: 1, backgroundColor: cores.fundoApp },
  centralizado: { flex: 1, backgroundColor: cores.fundoApp, alignItems: 'center', justifyContent: 'center', padding: espacamento.xl },
  textoErro: { color: cores.textoSecundario, textAlign: 'center', fontSize: 14 },
  lista: { padding: espacamento.lg, paddingTop: espacamento.xl, paddingBottom: espacamento.xl * 2 },
  titulo: { color: cores.texto, fontSize: 26, fontWeight: '700' },
  legenda: { color: cores.textoApagado, fontSize: 12, marginTop: 2, marginBottom: espacamento.lg, lineHeight: 17 },
  campo: { marginBottom: espacamento.md },
  linhaCampos: { flexDirection: 'row', gap: espacamento.md },
  rotuloCampo: { color: cores.textoApagado, fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.3, marginBottom: 6 },
  input: {
    backgroundColor: cores.fundoCard,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: cores.borda,
    paddingHorizontal: espacamento.md,
    paddingVertical: 12,
    color: cores.texto,
    fontSize: 15,
  },
  botao: { backgroundColor: cores.destaque, borderRadius: 10, paddingVertical: 14, alignItems: 'center', marginTop: espacamento.sm },
  botaoDesabilitado: { opacity: 0.6 },
  textoBotao: { color: cores.fundoApp, fontWeight: '700', fontSize: 15 },
  textoStatus: { color: cores.textoSecundario, fontSize: 12, lineHeight: 17, marginTop: espacamento.md },
  blocoResultado: {
    marginTop: espacamento.md,
    backgroundColor: cores.fundoCard,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: cores.borda,
    padding: espacamento.md,
    gap: 6,
  },
  linhaResultado: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 4 },
  rotuloResultado: { color: cores.textoSecundario, fontSize: 13 },
  valorResultado: { color: cores.destaque, fontWeight: '700', fontSize: 15 },
  subtitulo: { color: cores.destaque, fontSize: 12, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.6, marginTop: espacamento.xl, marginBottom: espacamento.sm },
  aviso: { color: cores.neutro, fontSize: 13, lineHeight: 19 },
  linhaSalva: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    backgroundColor: cores.fundoCard,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: cores.borda,
    padding: espacamento.md,
    marginBottom: espacamento.sm,
  },
  tickerSalvo: { color: cores.texto, fontWeight: '700', fontSize: 14 },
  dataSalva: { color: cores.textoApagado, fontSize: 11, marginTop: 2 },
  valorSalvo: { color: cores.texto, fontWeight: '700', fontSize: 14 },
  valorSalvoMargem: { color: cores.textoSecundario, fontSize: 11, marginTop: 2 },
});
