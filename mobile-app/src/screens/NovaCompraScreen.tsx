import React, { useState } from 'react';
import {
  ActivityIndicator,
  Alert,
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
import { cores, espacamento } from '../theme';
import { Badge } from '../components/Badge';

/**
 * Registra uma nova compra/venda direto do celular — mas SEM escrever nos
 * seus dados de verdade daqui. O que acontece de fato: este formulário
 * cria um "pedido pendente" numa coleção separada do Firestore
 * (pendencias_compras). Da próxima vez que você clicar em
 * "🔄 Atualizar Dados" no app do PC, ele lê esse pedido, valida (ticker
 * parece da B3? quantidade e preço são números válidos?) e só então
 * adiciona na sua carteira de verdade — exatamente como se você tivesse
 * preenchido o formulário lá.
 *
 * Por quê essa volta? Porque a fonte da verdade continua sendo só o PC
 * (core/pendencias_celular.py) — assim nunca existem duas cópias dos seus
 * dados que possam divergir.
 */
const COLECAO_PENDENCIAS = 'pendencias_compras';

type StatusEnvio = 'idle' | 'enviando' | 'pendente' | 'aplicado' | 'erro';

export function NovaCompraScreen() {
  const [ticker, setTicker] = useState('');
  const [quantidade, setQuantidade] = useState('');
  const [preco, setPreco] = useState('');
  const [tipo, setTipo] = useState<'compra' | 'venda'>('compra');
  const [status, setStatus] = useState<StatusEnvio>('idle');
  const [mensagemErro, setMensagemErro] = useState<string | null>(null);

  function limparFormulario() {
    setTicker('');
    setQuantidade('');
    setPreco('');
  }

  async function enviar() {
    const tickerLimpo = ticker.trim().toUpperCase();
    const qtdNumero = Number(quantidade.replace(',', '.'));
    const precoNumero = Number(preco.replace(',', '.'));

    if (!tickerLimpo) {
      Alert.alert('Informe o ticker', 'Ex: PETR4');
      return;
    }
    if (!Number.isFinite(qtdNumero) || qtdNumero <= 0) {
      Alert.alert('Quantidade inválida', 'Informe um número maior que zero.');
      return;
    }
    if (!Number.isFinite(precoNumero) || precoNumero <= 0) {
      Alert.alert('Preço inválido', 'Informe um número maior que zero.');
      return;
    }

    setStatus('enviando');
    setMensagemErro(null);

    try {
      const referencia = await addDoc(collection(db, COLECAO_PENDENCIAS), {
        ticker: tickerLimpo,
        quantidade: qtdNumero,
        precoUnitario: precoNumero,
        tipo,
        criadoEm: serverTimestamp(),
        status: 'pendente',
      });
      setStatus('pendente');

      // Escuta esse pedido específico pra avisar quando o PC aplicar (ou rejeitar).
      const cancelarInscricao = onSnapshot(doc(db, COLECAO_PENDENCIAS, referencia.id), (snap) => {
        const dadosDoc = snap.data();
        if (!dadosDoc) return;
        if (dadosDoc.status === 'aplicado') {
          setStatus('aplicado');
          limparFormulario();
          cancelarInscricao();
        } else if (dadosDoc.status === 'erro') {
          setStatus('erro');
          setMensagemErro(dadosDoc.mensagemErro ?? 'Não foi possível aplicar esse pedido.');
          cancelarInscricao();
        }
      });
    } catch {
      setStatus('erro');
      setMensagemErro('Falha ao enviar. Confira sua conexão com a internet.');
    }
  }

  return (
    <KeyboardAvoidingView
      style={estilos.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView contentContainerStyle={estilos.conteudo} keyboardShouldPersistTaps="handled">
        <Text style={estilos.titulo}>Nova Compra</Text>
        <Text style={estilos.legenda}>
          Isso é enviado pra nuvem como um pedido — sua carteira só é atualizada de verdade quando o app do
          PC estiver aberto e você clicar em "🔄 Atualizar Dados" (registrado com a data de hoje, sem taxas
          — ajuste depois no PC se precisar).
        </Text>

        <View style={estilos.seletorTipo}>
          <TouchableOpacity
            style={[estilos.opcaoTipo, tipo === 'compra' && estilos.opcaoTipoAtiva]}
            onPress={() => setTipo('compra')}
          >
            <Text style={[estilos.textoOpcaoTipo, tipo === 'compra' && estilos.textoOpcaoTipoAtiva]}>Compra</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[estilos.opcaoTipo, tipo === 'venda' && estilos.opcaoTipoAtiva]}
            onPress={() => setTipo('venda')}
          >
            <Text style={[estilos.textoOpcaoTipo, tipo === 'venda' && estilos.textoOpcaoTipoAtiva]}>Venda</Text>
          </TouchableOpacity>
        </View>

        <Campo rotulo="Ticker">
          <TextInput
            style={estilos.input}
            placeholder="Ex: PETR4"
            placeholderTextColor={cores.textoApagado}
            autoCapitalize="characters"
            maxLength={10}
            value={ticker}
            onChangeText={setTicker}
          />
        </Campo>

        <Campo rotulo="Quantidade">
          <TextInput
            style={estilos.input}
            placeholder="Ex: 100"
            placeholderTextColor={cores.textoApagado}
            keyboardType="numeric"
            value={quantidade}
            onChangeText={setQuantidade}
          />
        </Campo>

        <Campo rotulo={`Preço Unit. de ${tipo === 'venda' ? 'Venda' : 'Compra'} (R$)`}>
          <TextInput
            style={estilos.input}
            placeholder="Ex: 32,10"
            placeholderTextColor={cores.textoApagado}
            keyboardType="decimal-pad"
            value={preco}
            onChangeText={setPreco}
          />
        </Campo>

        <TouchableOpacity
          style={[estilos.botao, status === 'enviando' && estilos.botaoDesabilitado]}
          onPress={enviar}
          disabled={status === 'enviando'}
        >
          {status === 'enviando' ? (
            <ActivityIndicator color={cores.fundoApp} />
          ) : (
            <Text style={estilos.textoBotao}>Enviar {tipo === 'venda' ? 'Venda' : 'Compra'}</Text>
          )}
        </TouchableOpacity>

        {status === 'pendente' && (
          <View style={estilos.blocoStatus}>
            <Badge texto="⏳ Pendente" tipo="info" />
            <Text style={estilos.textoStatus}>
              Enviado! Aguardando o app do PC estar aberto e sincronizar.
            </Text>
          </View>
        )}
        {status === 'aplicado' && (
          <View style={estilos.blocoStatus}>
            <Badge texto="✅ Aplicado" tipo="ok" />
            <Text style={estilos.textoStatus}>Pronto — já entrou na sua carteira.</Text>
          </View>
        )}
        {status === 'erro' && (
          <View style={estilos.blocoStatus}>
            <Badge texto="⚠️ Não aplicado" tipo="warn" />
            <Text style={estilos.textoStatus}>{mensagemErro}</Text>
          </View>
        )}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

function Campo({ rotulo, children }: { rotulo: string; children: React.ReactNode }) {
  return (
    <View style={estilos.campo}>
      <Text style={estilos.rotuloCampo}>{rotulo}</Text>
      {children}
    </View>
  );
}

const estilos = StyleSheet.create({
  container: { flex: 1, backgroundColor: cores.fundoApp },
  conteudo: { padding: espacamento.lg, paddingTop: espacamento.xl, paddingBottom: espacamento.xl * 2 },
  titulo: { color: cores.texto, fontSize: 26, fontWeight: '700' },
  legenda: { color: cores.textoApagado, fontSize: 12, marginTop: 4, marginBottom: espacamento.lg, lineHeight: 17 },
  seletorTipo: { flexDirection: 'row', gap: espacamento.sm, marginBottom: espacamento.lg },
  opcaoTipo: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: cores.borda,
    alignItems: 'center',
  },
  opcaoTipoAtiva: { backgroundColor: 'rgba(212,175,55,0.14)', borderColor: cores.destaque },
  textoOpcaoTipo: { color: cores.textoSecundario, fontWeight: '600', fontSize: 13 },
  textoOpcaoTipoAtiva: { color: cores.destaque },
  campo: { marginBottom: espacamento.md },
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
});
