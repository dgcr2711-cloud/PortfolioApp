/**
 * Configuração do Firebase para o app do celular.
 *
 * Os valores abaixo são PÚBLICOS por natureza (é assim que o Firebase
 * funciona: a configuração de um app cliente sempre vai "dentro" do
 * aplicativo, não tem como esconder). O que protege seus dados de verdade
 * são as REGRAS DE SEGURANÇA do Firestore, configuradas no console — ver
 * o passo 4 do README_MOBILE.md. Ainda assim, nunca cometa (git commit)
 * este arquivo já preenchido num repositório público.
 *
 * Preencha com os valores que aparecem em: Firebase Console -> ⚙️
 * Configurações do projeto -> Seus apps -> app Web -> "SDK setup and
 * configuration" -> "Config".
 */
import { initializeApp } from 'firebase/app';
import { getAuth, getReactNativePersistence, initializeAuth } from 'firebase/auth';
import { getFirestore } from 'firebase/firestore';
import AsyncStorage from '@react-native-async-storage/async-storage';

const configuracaoFirebase = {
  apiKey: 'AIzaSyCyO7mGAF9cTKcHyE7pR1pdqbu_OFAon0Y',
  authDomain: 'meu-portfolio-b3.firebaseapp.com',
  projectId: 'meu-portfolio-b3',
  storageBucket: 'meu-portfolio-b3.firebasestorage.app',
  messagingSenderId: '966891446641',
  appId: '1:966891446641:web:0c478c4e20f2aa6a8916d0',
};

const app = initializeApp(configuracaoFirebase);
export const db = getFirestore(app);

// Login anônimo (ver src/contexts/AuthContext.tsx) — o Firebase dá ao app
// uma identidade técnica sem pedir e-mail/senha nenhum, só pra satisfazer a
// regra "request.auth != null" do Firestore (ver README_MOBILE.md, seção de
// segurança). `getReactNativePersistence` guarda essa identidade no
// AsyncStorage do celular, pra não precisar logar de novo a cada abertura
// do app. `initializeAuth` só pode ser chamado UMA vez por app — o try/catch
// é só uma defesa contra o modo de desenvolvimento (Fast Refresh do Expo
// pode reavaliar este arquivo mais de uma vez); no celular de verdade,
// nunca cai no catch.
export const auth = (() => {
  try {
    return initializeAuth(app, { persistence: getReactNativePersistence(AsyncStorage) });
  } catch {
    return getAuth(app);
  }
})();

export const COLECAO_FIRESTORE = 'portfolio';
export const DOCUMENTO_FIRESTORE = 'snapshot';
