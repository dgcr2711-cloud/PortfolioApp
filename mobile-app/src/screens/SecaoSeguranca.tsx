import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, Alert } from 'react-native';
import { usePin } from '../contexts/PinContext';
import { useAuth } from '../contexts/AuthContext';
import { cores, espacamento } from '../theme';

const TAMANHO_PIN = 4;
const TECLAS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '', '0', '⌫'];

type Etapa = 'status' | 'pedirAtualParaAlterar' | 'pedirAtualParaRemover' | 'criarNovo' | 'confirmarNovo';

/**
 * Aba "Mais → Segurança": onde o PIN pode ser criado (se foi recusado na
 * oferta inicial), alterado ou removido — sempre pedindo o PIN atual antes
 * de trocar ou remover, pra alguém que pegue o celular já destravado não
 * conseguir desativar a proteção sem saber o PIN.
 */
export function SecaoSeguranca() {
  const { pinConfigurado, verificarPin, configurarPin, removerPin } = usePin();
  const { sair } = useAuth();

  const [etapa, setEtapa] = useState<Etapa>('status');
  const [pinDigitado, setPinDigitado] = useState('');
  const [pinNovoProvisorio, setPinNovoProvisorio] = useState('');
  const [erro, setErro] = useState('');
  const [mensagemSucesso, setMensagemSucesso] = useState('');

  const aoTocarSairDaConta = () => {
    Alert.alert('Sair da conta?', 'Você vai precisar do e-mail e da senha de novo para entrar.', [
      { text: 'Cancelar', style: 'cancel' },
      { text: 'Sair', style: 'destructive', onPress: () => sair() },
    ]);
  };

  const reiniciar = (proximaEtapa: Etapa = 'status') => {
    setEtapa(proximaEtapa);
    setPinDigitado('');
    setPinNovoProvisorio('');
    setErro('');
  };

  const aoTocarTecla = async (tecla: string) => {
    if (tecla === '') return;
    setErro('');

    if (tecla === '⌫') {
      setPinDigitado((atual) => atual.slice(0, -1));
      return;
    }
    if (pinDigitado.length >= TAMANHO_PIN) return;
    const novoPin = pinDigitado + tecla;
    setPinDigitado(novoPin);
    if (novoPin.length !== TAMANHO_PIN) return;

    if (etapa === 'pedirAtualParaAlterar' || etapa === 'pedirAtualParaRemover') {
      const correto = await verificarPin(novoPin);
      if (!correto) {
        setErro('PIN incorreto.');
        setPinDigitado('');
        return;
      }
      if (etapa === 'pedirAtualParaRemover') {
        await removerPin();
        setMensagemSucesso('PIN removido. O app não vai mais pedir PIN ao abrir.');
        reiniciar('status');
      } else {
        setPinDigitado('');
        setEtapa('criarNovo');
      }
    } else if (etapa === 'criarNovo') {
      setPinNovoProvisorio(novoPin);
      setPinDigitado('');
      setEtapa('confirmarNovo');
    } else if (etapa === 'confirmarNovo') {
      if (novoPin === pinNovoProvisorio) {
        await configurarPin(novoPin);
        setMensagemSucesso('PIN salvo com sucesso.');
        reiniciar('status');
      } else {
        setErro('Os PINs não bateram. Vamos tentar de novo.');
        reiniciar('criarNovo');
      }
    }
  };

  if (etapa === 'status') {
    return (
      <ScrollView contentContainerStyle={estilos.containerStatus}>
        <Text style={estilos.icone}>🔒</Text>
        <Text style={estilos.tituloStatus}>{pinConfigurado ? 'PIN ativo' : 'PIN não configurado'}</Text>
        <Text style={estilos.descricaoStatus}>
          {pinConfigurado
            ? 'O app pede o PIN sempre que é aberto ou volta de segundo plano.'
            : 'Qualquer pessoa com este celular destravado consegue abrir o app e ver sua carteira.'}
        </Text>
        {mensagemSucesso ? <Text style={estilos.textoSucesso}>{mensagemSucesso}</Text> : null}

        <TouchableOpacity
          style={estilos.botaoPrimario}
          onPress={() => reiniciar(pinConfigurado ? 'pedirAtualParaAlterar' : 'criarNovo')}
        >
          <Text style={estilos.textoBotaoPrimario}>{pinConfigurado ? 'Alterar PIN' : 'Criar PIN'}</Text>
        </TouchableOpacity>

        {pinConfigurado && (
          <TouchableOpacity style={estilos.botaoPerigo} onPress={() => reiniciar('pedirAtualParaRemover')}>
            <Text style={estilos.textoBotaoPerigo}>Remover PIN</Text>
          </TouchableOpacity>
        )}

        <View style={estilos.divisor} />

        <Text style={estilos.tituloStatus}>Conta</Text>
        <Text style={estilos.descricaoStatus}>
          Seu login com e-mail e senha protege o acesso à sua carteira na nuvem.
        </Text>
        <TouchableOpacity style={estilos.botaoPerigo} onPress={aoTocarSairDaConta}>
          <Text style={estilos.textoBotaoPerigo}>Sair da conta</Text>
        </TouchableOpacity>
      </ScrollView>
    );
  }

  const titulo =
    etapa === 'pedirAtualParaAlterar' || etapa === 'pedirAtualParaRemover'
      ? 'Digite o PIN atual'
      : etapa === 'criarNovo'
      ? 'Crie um PIN de 4 dígitos'
      : 'Confirme o novo PIN';

  return (
    <View style={estilos.container}>
      <Text style={estilos.titulo}>{titulo}</Text>
      <View style={estilos.linhaBolinhas}>
        {Array.from({ length: TAMANHO_PIN }).map((_, i) => (
          <View key={i} style={[estilos.bolinha, i < pinDigitado.length && estilos.bolinhaPreenchida]} />
        ))}
      </View>
      {erro ? <Text style={estilos.textoErro}>{erro}</Text> : null}
      <View style={estilos.teclado}>
        {TECLAS.map((tecla, i) => (
          <TouchableOpacity
            key={i}
            style={[estilos.tecla, tecla === '' && estilos.teclaInvisivel]}
            disabled={tecla === ''}
            onPress={() => aoTocarTecla(tecla)}
          >
            <Text style={estilos.textoTecla}>{tecla}</Text>
          </TouchableOpacity>
        ))}
      </View>
      <TouchableOpacity style={estilos.botaoCancelar} onPress={() => reiniciar('status')}>
        <Text style={estilos.textoBotaoCancelar}>Cancelar</Text>
      </TouchableOpacity>
    </View>
  );
}

const estilos = StyleSheet.create({
  containerStatus: { padding: espacamento.xl, alignItems: 'center' },
  container: { flex: 1, alignItems: 'center', paddingTop: espacamento.xl },
  icone: { fontSize: 36, marginBottom: espacamento.md },
  tituloStatus: { color: cores.texto, fontSize: 18, fontWeight: '600', marginBottom: espacamento.sm },
  descricaoStatus: {
    color: cores.textoSecundario,
    fontSize: 14,
    textAlign: 'center',
    marginBottom: espacamento.lg,
    lineHeight: 20,
  },
  textoSucesso: { color: cores.positivo, marginBottom: espacamento.lg, textAlign: 'center' },
  divisor: { width: '100%', height: 1, backgroundColor: cores.borda, marginVertical: espacamento.xl },
  titulo: { color: cores.texto, fontSize: 18, fontWeight: '600', marginBottom: espacamento.lg },
  linhaBolinhas: { flexDirection: 'row', gap: espacamento.md, marginBottom: espacamento.lg },
  bolinha: { width: 14, height: 14, borderRadius: 7, borderWidth: 2, borderColor: cores.borda },
  bolinhaPreenchida: { backgroundColor: cores.destaque, borderColor: cores.destaque },
  textoErro: { color: cores.negativo, marginBottom: espacamento.md, textAlign: 'center' },
  teclado: { flexDirection: 'row', flexWrap: 'wrap', width: 250, justifyContent: 'center' },
  tecla: {
    width: 70,
    height: 70,
    borderRadius: 35,
    alignItems: 'center',
    justifyContent: 'center',
    margin: espacamento.xs,
    backgroundColor: cores.fundoCard,
  },
  teclaInvisivel: { backgroundColor: 'transparent' },
  textoTecla: { color: cores.texto, fontSize: 24, fontWeight: '500' },
  botaoPrimario: {
    backgroundColor: cores.destaque,
    paddingVertical: espacamento.md,
    paddingHorizontal: espacamento.xl,
    borderRadius: 10,
    marginTop: espacamento.sm,
    minWidth: 220,
    alignItems: 'center',
  },
  textoBotaoPrimario: { color: cores.fundoApp, fontSize: 16, fontWeight: '700' },
  botaoPerigo: { paddingVertical: espacamento.md, marginTop: espacamento.sm, minWidth: 220, alignItems: 'center' },
  textoBotaoPerigo: { color: cores.negativo, fontSize: 14, fontWeight: '600' },
  botaoCancelar: { paddingVertical: espacamento.md, marginTop: espacamento.lg },
  textoBotaoCancelar: { color: cores.textoSecundario, fontSize: 14 },
});
