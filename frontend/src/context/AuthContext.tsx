import {
  createContext,
  useContext,
  useReducer,
  useEffect,
  useLayoutEffect,
  type ReactNode,
} from 'react'
import type { User } from '@/types/auth'
import type { AuthAction } from '@/types/AuthContextTypes'
import { registerOnAccessTokenRefreshed, setAccessToken } from '@/api/authToken'

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

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(authReducer, initialState)

  useLayoutEffect(() => {
    setAccessToken(state.accessToken)
  }, [state.accessToken])

  useEffect(() => {
    return registerOnAccessTokenRefreshed((token) => {
      dispatch({ type: 'SET_ACCESS_TOKEN', payload: token })
    })
  }, [])

  useEffect(() => {
    // Attempt a silent refresh on mount. If a valid httpOnly cookie exists,
    // the user is restored without seeing the login page.
    import('@/api/authRefresh').then(({ silentRefresh }) => {
      silentRefresh(dispatch).finally(() => {
        dispatch({ type: 'SET_LOADING', payload: false })
      })
    })
  }, [])

  return (
    <AuthContext.Provider value={{ state, dispatch }}>
      {children}
    </AuthContext.Provider>
  )
}
