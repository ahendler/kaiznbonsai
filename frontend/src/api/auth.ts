import api from '@/api/client'
import { REFRESH_TOKEN_KEY } from '@/api/authRefresh'
import type { AuthTokens, User } from '@/types/auth'

interface LoginPayload {
  email: string
  password: string
}

interface RegisterPayload {
  email: string
  password: string
  password_confirm: string
}

export const authApi = {
  register: (payload: RegisterPayload) =>
    api.post('/auth/register/', payload).then((r) => r.data),

  login: (payload: LoginPayload) =>
    api.post<AuthTokens>('/auth/login/', payload).then((r) => {
      // Keep the sessionStorage fallback copy in sync with the refresh
      // token the backend bakes into the httpOnly cookie on login.
      if (r.data.refresh) {
        sessionStorage.setItem(REFRESH_TOKEN_KEY, r.data.refresh as string)
      }
      return r.data
    }),

  logout: () => {
    // Clear the fallback copy before the server-side blacklist so a failed
    // network request cannot leave a dangling token in sessionStorage.
    sessionStorage.removeItem(REFRESH_TOKEN_KEY)
    return api.post('/auth/logout/')
  },

  me: () => api.get<User>('/auth/me/').then((r) => r.data),
}
