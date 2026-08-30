import React, { useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
} from 'react-native';
import { useAuth } from '../contexts/AuthContext';
import { cores, espacamento } from '../theme';

/**
 * Tela cheia mostrada quando ninguém está logado no Firebase — substitui o
 * antigo login anônimo automático. Só existe UMA conta de verdade (a sua,
 * criada por você no Console do Firebase — ver README_MOBILE.md), então
 * não tem "criar conta" aqui de propósito: este app é só seu.
 */
export function TelaLogin() {
  const { entrar } = useAuth();
  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const [entrando, setEntrando] = useState(false);
  const [erro, setErro] = useState('');

  const podeEntrar = email.trim().length > 0 && senha.length > 0 && !entrando;

  async function aoTocarEntrar() {
    if (!podeEntrar) return;
    setEntrando(true);
    setErro('');
    try {
      await entrar(email, senha);
      // Sucesso: onAuthStateChanged (AuthContext) atualiza sozinho e o App
      // troca de tela — nada a fazer aqui além de deixar `entrando` true
      // até a troca de tela acontecer.
    } catch (erroLogin: any) {
      setErro(mensagemDeErro(erroLogin?.code));
      setEntrando(false);
    }
  }

  return (
    <KeyboardAvoidingView
      style={estilos.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <Text style={estilos.icone}>🔐</Text>
      <Text style={estilos.titulo}>Entrar</Text>
      <Text style={estilos.subtitulo}>
        Use o e-mail e a senha que você criou no Console do Firebase (ver README_MOBILE.md).
      </Text>

      <TextInput
        style={estilos.campo}
        placeholder="E-mail"
        placeholderTextColor={cores.textoApagado}
        autoCapitalize="none"
        autoCorrect={false}
        keyboardType="email-address"
        value={email}
        onChangeText={(texto: string) => {
          setEmail(texto);
          setErro('');
        }}
        editable={!entrando}
      />
      <TextInput
        style={estilos.campo}
        placeholder="Senha"
        placeholderTextColor={cores.textoApagado}
        secureTextEntry
        value={senha}
        onChangeText={(texto: string) => {
          setSenha(texto);
          setErro('');
        }}
        editable={!entrando}
        onSubmitEditing={aoTocarEntrar}
      />

      {erro ? <Text style={estilos.textoErro}>{erro}</Text> : null}

      <TouchableOpacity
        style={[estilos.botaoPrimario, !podeEntrar && estilos.botaoDesabilitado]}
        onPress={aoTocarEntrar}
        disabled={!podeEntrar}
      >
        {entrando ? (
          <ActivityIndicator color={cores.fundoApp} />
        ) : (
          <Text style={estilos.textoBotaoPrimario}>Entrar</Text>
        )}
      </TouchableOpacity>
    </KeyboardAvoidingView>
  );
}

function mensagemDeErro(codigo?: string): string {
  switch (codigo) {
    case 'auth/invalid-email':
      return 'E-mail em um formato inválido.';
    case 'auth/user-not-found':
    case 'auth/invalid-credential':
    case 'auth/wrong-password':
      return 'E-mail ou senha incorretos.';
    case 'auth/too-many-requests':
      return 'Muitas tentativas erradas — espere um pouco e tente de novo.';
    case 'auth/network-request-failed':
      return 'Sem conexão com a internet.';
    default:
      return 'Não foi possível entrar. Confira o e-mail e a senha.';
  }
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
  titulo: { color: cores.texto, fontSize: 22, fontWeight: '700', marginBottom: espacamento.sm },
  subtitulo: {
    color: cores.textoSecundario,
    fontSize: 13,
    textAlign: 'center',
    marginBottom: espacamento.xl,
    lineHeight: 19,
  },
  campo: {
    width: '100%',
    backgroundColor: cores.fundoCard,
    borderWidth: 1,
    borderColor: cores.borda,
    borderRadius: 10,
    paddingHorizontal: espacamento.md,
    paddingVertical: espacamento.md,
    color: cores.texto,
    fontSize: 15,
    marginBottom: espacamento.sm,
  },
  textoErro: {
    color: cores.negativo,
    fontSize: 13,
    textAlign: 'center',
    marginTop: espacamento.xs,
    marginBottom: espacamento.sm,
  },
  botaoPrimario: {
    backgroundColor: cores.destaque,
    paddingVertical: espacamento.md,
    borderRadius: 10,
    width: '100%',
    alignItems: 'center',
    marginTop: espacamento.sm,
  },
  botaoDesabilitado: { opacity: 0.5 },
  textoBotaoPrimario: { color: cores.fundoApp, fontSize: 16, fontWeight: '700' },
});
