import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { usePin } from '../contexts/PinContext';
import { cores, espacamento } from '../theme';

const TAMANHO_PIN = 4;
const TECLAS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '', '0', '⌫'];

/**
 * Tela cheia mostrada quando o app está bloqueado: tanto na oferta inicial
 * de criar um PIN quanto na hora de digitar o PIN pra desbloquear.
 */
export function TelaPin() {
  const { pinConfigurado, pinRecusado, configurarPin, verificarPin, recusarPinPorAgora } = usePin();

  // Oferta inicial: primeira vez que o app abre, sem PIN configurado nem
  // recusado ainda — pergunta se quer proteger o app antes de forçar nada.
  const [mostrarOferta, setMostrarOferta] = useState(!pinConfigurado && !pinRecusado);

  const [modo, setModo] = useState<'digitar' | 'criar' | 'confirmar'>(pinConfigurado ? 'digitar' : 'criar');
  const [pinDigitado, setPinDigitado] = useState('');
  const [primeiroPin, setPrimeiroPin] = useState('');
  const [erro, setErro] = useState('');

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

    if (modo === 'digitar') {
      const correto = await verificarPin(novoPin);
      if (!correto) {
        setErro('PIN incorreto. Tente novamente.');
        setPinDigitado('');
      }
    } else if (modo === 'criar') {
      setPrimeiroPin(novoPin);
      setPinDigitado('');
      setModo('confirmar');
    } else if (modo === 'confirmar') {
      if (novoPin === primeiroPin) {
        await configurarPin(novoPin);
      } else {
        setErro('Os PINs não bateram. Vamos tentar de novo.');
        setPinDigitado('');
        setPrimeiroPin('');
        setModo('criar');
      }
    }
  };

  if (mostrarOferta) {
    return (
      <View style={estilos.container}>
        <Text style={estilos.icone}>🔒</Text>
        <Text style={estilos.titulo}>Proteger o app com um PIN?</Text>
        <Text style={estilos.subtitulo}>
          Um PIN de 4 dígitos impede que alguém que pegar seu celular destravado veja sua carteira sem
          digitar o código. Você pode ativar isso a qualquer momento depois, em "Mais → Segurança".
        </Text>
        <TouchableOpacity
          style={estilos.botaoPrimario}
          onPress={() => {
            setMostrarOferta(false);
            setModo('criar');
          }}
        >
          <Text style={estilos.textoBotaoPrimario}>Criar PIN agora</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={estilos.botaoSecundario}
          onPress={async () => {
            await recusarPinPorAgora();
          }}
        >
          <Text style={estilos.textoBotaoSecundario}>Agora não</Text>
        </TouchableOpacity>
      </View>
    );
  }

  const titulo =
    modo === 'digitar' ? 'Digite seu PIN' : modo === 'criar' ? 'Crie um PIN de 4 dígitos' : 'Confirme o PIN';

  return (
    <View style={estilos.container}>
      <Text style={estilos.icone}>🔒</Text>
      <Text style={estilos.titulo}>{titulo}</Text>

      <View style={estilos.linhaBolinhas}>
        {Array.from({ length: TAMANHO_PIN }).map((_, i) => (
          <View
            key={i}
            style={[estilos.bolinha, i < pinDigitado.length && estilos.bolinhaPreenchida]}
          />
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
    </View>
  );
}

const estilos = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: cores.fundoApp,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: espacamento.xl,
  },
  icone: { fontSize: 40, marginBottom: espacamento.md },
  titulo: { color: cores.texto, fontSize: 20, fontWeight: '600', textAlign: 'center', marginBottom: espacamento.sm },
  subtitulo: {
    color: cores.textoSecundario,
    fontSize: 14,
    textAlign: 'center',
    marginBottom: espacamento.xl,
    lineHeight: 20,
  },
  linhaBolinhas: { flexDirection: 'row', gap: espacamento.md, marginVertical: espacamento.xl },
  bolinha: {
    width: 16,
    height: 16,
    borderRadius: 8,
    borderWidth: 2,
    borderColor: cores.borda,
  },
  bolinhaPreenchida: { backgroundColor: cores.destaque, borderColor: cores.destaque },
  textoErro: { color: cores.negativo, marginBottom: espacamento.lg, textAlign: 'center' },
  teclado: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    width: 260,
    justifyContent: 'center',
    marginTop: espacamento.lg,
  },
  tecla: {
    width: 76,
    height: 76,
    borderRadius: 38,
    alignItems: 'center',
    justifyContent: 'center',
    margin: espacamento.xs,
    backgroundColor: cores.fundoCard,
  },
  teclaInvisivel: { backgroundColor: 'transparent' },
  textoTecla: { color: cores.texto, fontSize: 26, fontWeight: '500' },
  botaoPrimario: {
    backgroundColor: cores.destaque,
    paddingVertical: espacamento.md,
    paddingHorizontal: espacamento.xl,
    borderRadius: 10,
    marginTop: espacamento.md,
    width: '100%',
    alignItems: 'center',
  },
  textoBotaoPrimario: { color: cores.fundoApp, fontSize: 16, fontWeight: '700' },
  botaoSecundario: { paddingVertical: espacamento.md, alignItems: 'center' },
  textoBotaoSecundario: { color: cores.textoSecundario, fontSize: 14 },
});
