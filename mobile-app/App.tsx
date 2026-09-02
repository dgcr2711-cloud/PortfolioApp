import React from 'react';
import { StatusBar } from 'expo-status-bar';
import { NavigationContainer, DarkTheme } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { Text, View } from 'react-native';
import { VisaoGeralScreen } from './src/screens/VisaoGeralScreen';
import { CarteiraScreen } from './src/screens/CarteiraScreen';
import { FundamentosScreen } from './src/screens/FundamentosScreen';
import { ComprasScreen } from './src/screens/ComprasScreen';
import { MaisScreen } from './src/screens/MaisScreen';
import { TelaPin } from './src/screens/TelaPin';
import { TelaLogin } from './src/screens/TelaLogin';
import { OcultarValoresProvider } from './src/contexts/OcultarValoresContext';
import { PinProvider, usePin } from './src/contexts/PinContext';
import { AuthProvider, useAuth } from './src/contexts/AuthContext';
import { cores } from './src/theme';

const Tab = createBottomTabNavigator();

// Tema escuro do react-navigation, ajustado pra nossa paleta (fundo/dourado)
// em vez do azul padrão do DarkTheme.
const temaEscuro = {
  ...DarkTheme,
  colors: {
    ...DarkTheme.colors,
    background: cores.fundoApp,
    card: cores.fundoCard,
    border: cores.borda,
    primary: cores.destaque,
    text: cores.texto,
  },
};

const ICONE_POR_ABA: Record<string, string> = {
  'Visão Geral': '🏠',
  Carteira: '📈',
  Fundamentos: '🔎',
  Compras: '🧾',
  Mais: '⋯',
};

/**
 * Fica DENTRO do PinProvider e do AuthProvider (pra poder usar usePin() e
 * useAuth()) mas FORA do NavigationContainer: enquanto o app estiver
 * bloqueado pelo PIN, ou ninguém tiver feito login no Firebase ainda,
 * mostra só a tela correspondente — a navegação e as telas da carteira nem
 * chegam a montar, então nenhuma delas tenta ler o Firestore antes da hora
 * nem "passa por trás" da trava de PIN.
 */
function ConteudoComTravaPin() {
  const { carregando, pinConfigurado, pinRecusado, desbloqueado } = usePin();
  const { carregando: carregandoAuth, autenticado } = useAuth();

  if (carregando) {
    // Ainda checando se existe um PIN salvo — tela em branco por uma fração
    // de segundo é melhor do que mostrar a carteira e "piscar" a trava depois.
    return <View style={{ flex: 1, backgroundColor: cores.fundoApp }} />;
  }

  const precisaMostrarTravaPin = !desbloqueado && (pinConfigurado || !pinRecusado);
  if (precisaMostrarTravaPin) {
    return <TelaPin />;
  }

  if (carregandoAuth) {
    // Checando se já existe uma sessão salva no aparelho (login anterior) —
    // tela em branco em vez de mostrar a tela de login "piscando" à toa.
    return <View style={{ flex: 1, backgroundColor: cores.fundoApp }} />;
  }

  if (!autenticado) {
    return <TelaLogin />;
  }

  return (
    <NavigationContainer theme={temaEscuro}>
      <StatusBar style="light" />
      <Tab.Navigator
        screenOptions={({ route }) => ({
          headerShown: false,
          tabBarActiveTintColor: cores.destaque,
          tabBarInactiveTintColor: cores.textoSecundario,
          tabBarStyle: { backgroundColor: cores.fundoCard, borderTopColor: cores.borda },
          tabBarIcon: () => <Text style={{ fontSize: 18 }}>{ICONE_POR_ABA[route.name]}</Text>,
        })}
      >
        <Tab.Screen name="Visão Geral" component={VisaoGeralScreen} />
        <Tab.Screen name="Carteira" component={CarteiraScreen} />
        <Tab.Screen name="Fundamentos" component={FundamentosScreen} />
        <Tab.Screen name="Compras" component={ComprasScreen} />
        <Tab.Screen name="Mais" component={MaisScreen} />
      </Tab.Navigator>
    </NavigationContainer>
  );
}

export default function App() {
  return (
    // SafeAreaProvider precisa envolver tudo (2026-09-02): é ele quem dá a
    // altura real da área segura do topo/fundo de CADA aparelho (notch,
    // Dynamic Island, barra de status) pros hooks useSafeAreaInsets()
    // (ver src/hooks/useEspacoTopo.ts) e também pra própria barra de abas
    // do react-navigation, que passa a respeitar sozinha a área de baixo
    // (ex: a "risquinho" de gesto do iPhone) sem precisar de nenhum código
    // extra aqui.
    <SafeAreaProvider>
      <PinProvider>
        <AuthProvider>
          <OcultarValoresProvider>
            <ConteudoComTravaPin />
          </OcultarValoresProvider>
        </AuthProvider>
      </PinProvider>
    </SafeAreaProvider>
  );
}
