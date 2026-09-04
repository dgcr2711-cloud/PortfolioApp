// Stub mínimo de firebase/firestore para o harness de verificação
// (2026-09-04) — ver nota em ../react/index.d.ts. Só a API realmente usada
// no projeto (doc/onSnapshot/addDoc/collection/serverTimestamp), com o
// mesmo formato baseado em callbacks/Promises da biblioteca real.
declare module 'firebase/firestore' {
  import type { FirebaseApp } from 'firebase/app';

  export interface Firestore {}
  export interface DocumentReference {
    id: string;
  }
  export interface CollectionReference {}
  export interface DocumentSnapshot {
    exists(): boolean;
    data(): any;
    id: string;
  }

  export function getFirestore(app: FirebaseApp): Firestore;
  export function doc(db: Firestore, colecao: string, id?: string): DocumentReference;
  export function collection(db: Firestore, caminho: string): CollectionReference;
  export function addDoc(colecao: CollectionReference, dados: any): Promise<DocumentReference>;
  export function serverTimestamp(): any;
  export function onSnapshot(
    referencia: DocumentReference,
    onNext: (snapshot: DocumentSnapshot) => void,
    onError?: (erro: Error) => void
  ): () => void;
}
