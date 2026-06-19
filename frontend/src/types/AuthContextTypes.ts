// Shared action type — kept separate to avoid circular imports between
// AuthContext.tsx (which imports authRefresh) and authRefresh.ts.
export type AuthAction =
  | { type: 'SET_AUTH'; payload: { token: string; user: import('./auth').User } }
  | { type: 'SET_ACCESS_TOKEN'; payload: string }
  | { type: 'CLEAR_AUTH' }
  | { type: 'SET_LOADING'; payload: boolean }
