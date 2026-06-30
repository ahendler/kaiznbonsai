import axios from 'axios'
import type { AuthAction } from '@/types/AuthContextTypes'
import type { User } from '@/types/auth'

export const REFRESH_TOKEN_KEY = 'kb_refresh_token'

const BASE = import.meta.env.VITE_API_URL ?? '' // unset in prod → same-origin /api/v1

// Module-level singleton — ensures only one refresh call is in flight at a time
// regardless of how many concurrent 401s arrive.
let _refreshPromise: Promise<string> | null = null

/**
 * Two-phase silent refresh:
 *
 * Phase 1: POST /auth/token/refresh/ with no body — the backend reads the
 *          httpOnly refresh cookie. This is the primary path.
 *
 * Phase 2: If Phase 1 fails (cookie blocked by browser privacy settings),
 *          fall back to the token stored in sessionStorage and send it in
 *          the request body. The backend accepts either source.
 */
export function getOrStartRefresh(): Promise<string> {
  if (!_refreshPromise) {
    const url = `${BASE}/api/v1/auth/token/refresh/`

    _refreshPromise = axios
      .post<{ access: string; refresh?: string }>(url, {}, { withCredentials: true })
      .then(({ data }) => {
        if (data.refresh) sessionStorage.setItem(REFRESH_TOKEN_KEY, data.refresh)
        return data.access
      })
      .catch(() => {
        const stored = sessionStorage.getItem(REFRESH_TOKEN_KEY)
        if (!stored) return Promise.reject(new Error('No refresh token available'))

        return axios
          .post<{ access: string; refresh?: string }>(url, { refresh: stored }, { withCredentials: true })
          .then(({ data }) => {
            if (data.refresh) sessionStorage.setItem(REFRESH_TOKEN_KEY, data.refresh)
            return data.access
          })
          .catch((err) => {
            sessionStorage.removeItem(REFRESH_TOKEN_KEY)
            return Promise.reject(err)
          })
      })
      .finally(() => {
        _refreshPromise = null
      })
  }

  return _refreshPromise
}

/**
 * Called by AuthProvider on mount. Attempts a silent refresh and, if
 * successful, fetches /auth/me/ to restore the full user object.
 */
export async function silentRefresh(
  dispatch: React.Dispatch<AuthAction>,
): Promise<void> {
  const token = await getOrStartRefresh()
  const { data: user } = await axios.get<User>(`${BASE}/api/v1/auth/me/`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  dispatch({ type: 'SET_AUTH', payload: { token, user } })
}
