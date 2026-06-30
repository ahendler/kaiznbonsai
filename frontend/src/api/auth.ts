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
    api.post<AuthTokens>('/auth/login/', payload).then((r) => r.data),

  logout: () => {
    sessionStorage.removeItem(REFRESH_TOKEN_KEY)
    return api.post('/auth/logout/')
  },

  me: () => api.get<User>('/auth/me/').then((r) => r.data),
}
