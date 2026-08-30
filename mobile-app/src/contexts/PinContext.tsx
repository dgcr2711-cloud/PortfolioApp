import React, { createContext, useContext, useEffect, useRef, useState } from 'react';
import { AppState, AppStateStatus } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { sha256Hex } from '../utils/sha256';

/**
 * PIN de acesso do app do celular — mitigação prática pedida na auditoria
 * (ADD-1 / "PIN de acesso no app do celular"): quem pegar o celular
 * destravado não consegue abrir o app e ver os números sem o PIN.
 *
 * Importante ser honesto sobre o alcance disto: é uma tranca NA TELA do
 * celular — impede que alguém com o celular (ou o app instalado) destravado
 * abra e veja a carteira sem saber o PIN. A proteção dos dados NA NUVEM é
 * outra camada, separada: ver src/contexts/AuthContext.tsx (login anônimo do
 * Firebase + regra "request.auth != null" no Firestore) — as duas juntas
 * cobrem "alguém pega meu celular destravado" (PIN) e "alguém sem o app
 * tenta ler meus dados direto" (login anônimo).
 *
 * O PIN nunca é guardado em texto puro: só o hash (SHA-256, ver
 * src/utils/sha256.ts) fica salvo no armazenamento do aparelho.
 *
 * "Esqueci o PIN": como não existe um servidor validando o PIN (é só uma
 * tranca local), não tem como "recuperar" o PIN antigo. A saída é remover o
 * app do celular e reinstalar (ou limpar os dados do Expo Go) — isso apaga
 * o PIN salvo, sem qualquer efeito nos dados da carteira, que continuam
 * seguros na nuvem e no PC.
 */

const CHAVE_HASH_PIN = '@portfolio_b3_pin_hash';
const CHAVE_PIN_RECUSADO = '@portfolio_b3_pin_recusado';

type PinContextType = {
  carregando: boolean;
  pinConfigurado: boolean;
  pinRecusado: boolean;
  desbloqueado: boolean;
  configurarPin: (pin: string) => Promise<void>;
  verificarPin: (pin: string) => Promise<boolean>;
  removerPin: () => Promise<void>;
  recusarPinPorAgora: () => Promise<void>;
  bloquearNovamente: () => void;
};

const PinContext = createContext<PinContextType | undefined>(undefined);

export function PinProvider({ children }: { children: React.ReactNode }) {
  const [carregando, setCarregando] = useState(true);
  const [hashSalvo, setHashSalvo] = useState<string | null>(null);
  const [pinRecusado, setPinRecusado] = useState(false);
  const [desbloqueado, setDesbloqueado] = useState(false);
  const pinConfiguradoRef = useRef(false);

  useEffect(() => {
    Promise.all([AsyncStorage.getItem(CHAVE_HASH_PIN), AsyncStorage.getItem(CHAVE_PIN_RECUSADO)])
      .then(([hash, recusado]) => {
        setHashSalvo(hash);
        setPinRecusado(recusado === '1');
      })
      .catch(() => {
        // Se der erro lendo o armazenamento local, trata como "sem PIN
        // configurado" — a leitura de dados da carteira nunca pode ficar
        // travada por causa de uma falha nesta checagem local.
        setHashSalvo(null);
        setPinRecusado(false);
      })
      .finally(() => setCarregando(false));
  }, []);

  useEffect(() => {
    pinConfiguradoRef.current = hashSalvo !== null;
  }, [hashSalvo]);

  useEffect(() => {
    // Re-trava o app sempre que ele volta do segundo plano (trocou de app,
    // bloqueou a tela do celular etc.) — sem isso, o PIN só protegeria a
    // primeiríssima abertura do processo, o que não protege muita coisa na
    // prática, já que apps costumam ficar "vivos" em segundo plano.
    const assinatura = AppState.addEventListener('change', (proximoEstado: AppStateStatus) => {
      if (proximoEstado !== 'active' && pinConfiguradoRef.current) {
        setDesbloqueado(false);
      }
    });
    return () => assinatura.remove();
  }, []);

  const configurarPin = async (pin: string) => {
    const hash = sha256Hex(pin);
    await AsyncStorage.setItem(CHAVE_HASH_PIN, hash);
    await AsyncStorage.removeItem(CHAVE_PIN_RECUSADO);
    setHashSalvo(hash);
    setPinRecusado(false);
    setDesbloqueado(true);
  };

  const verificarPin = async (pin: string) => {
    const correto = sha256Hex(pin) === hashSalvo;
    if (correto) setDesbloqueado(true);
    return correto;
  };

  const removerPin = async () => {
    await AsyncStorage.removeItem(CHAVE_HASH_PIN);
    setHashSalvo(null);
    setDesbloqueado(true); // sem PIN configurado, não faz sentido continuar bloqueado
  };

  const recusarPinPorAgora = async () => {
    await AsyncStorage.setItem(CHAVE_PIN_RECUSADO, '1');
    setPinRecusado(true);
    setDesbloqueado(true);
  };

  const bloquearNovamente = () => setDesbloqueado(false);

  return (
    <PinContext.Provider
      value={{
        carregando,
        pinConfigurado: hashSalvo !== null,
        pinRecusado,
        desbloqueado,
        configurarPin,
        verificarPin,
        removerPin,
        recusarPinPorAgora,
        bloquearNovamente,
      }}
    >
      {children}
    </PinContext.Provider>
  );
}

export function usePin(): PinContextType {
  const contexto = useContext(PinContext);
  if (!contexto) {
    throw new Error('usePin precisa ser usado dentro de um PinProvider');
  }
  return contexto;
}
