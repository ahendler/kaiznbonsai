import {
  createContext,
  useContext,
  useReducer,
  useEffect,
  type ReactNode,
} from 'react'
import type { User } from '@/types/auth'
import type { AuthAction } from '@/types/AuthContextTypes'

// ---------------------------------------------------------------------------
// State & actions
// ---------------------------------------------------------------------------

interface AuthState {
  accessToken: string | null
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean // true while the boot-time silent refresh is in flight
}

const initialState: AuthState = {
  accessToken: null,
  user: null,
  isAuthenticated: false,
  isLoading: true,
}

function authReducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case 'SET_AUTH':
      return {
        ...state,
        accessToken: action.payload.token,
        user: action.payload.user,
        isAuthenticated: true,
        isLoading: false,
      }
    case 'SET_ACCESS_TOKEN':
      return { ...state, accessToken: action.payload, isAuthenticated: true }
    case 'CLEAR_AUTH':
      return { ...initialState, isLoading: false }
    case 'SET_LOADING':
      return { ...state, isLoading: action.payload }
  }
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

interface AuthContextValue {
  state: AuthState
  dispatch: React.Dispatch<AuthAction>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

// Exported so the axios client can read the token without going through
// React hooks (interceptors run outside the component tree).
export let getAccessToken: () => string | null = () => null

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(authReducer, initialState)

  // Keep the module-level getter in sync with the reducer state so the
  // axios request interceptor always has the latest token.
  getAccessToken = () => state.accessToken

  useEffect(() => {
    // Attempt a silent refresh on mount. If a valid httpOnly cookie exists,
    // the user is restored without seeing the login page.
    import('@/api/authRefresh').then(({ silentRefresh }) => {
      silentRefresh(dispatch).finally(() => {
        dispatch({ type: 'SET_LOADING', payload: false })
      })
    })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <AuthContext.Provider value={{ state, dispatch }}>
      {children}
    </AuthContext.Provider>
  )
}
