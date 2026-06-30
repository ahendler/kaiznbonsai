import axios from 'axios'
import type { AuthAction } from '@/types/AuthContextTypes'
import type { User } from '@/types/auth'

const BASE = import.meta.env.VITE_API_URL ?? '' // unset in prod → same-origin /api/v1

// Module-level singleton — ensures only one refresh call is in flight at a time
// regardless of how many concurrent 401s arrive.
let _refreshPromise: Promise<string> | null = null

/**
 * Silent refresh via httpOnly cookie only.
 * POST /auth/token/refresh/ with an empty body; the backend reads the cookie.
 */
export function getOrStartRefresh(): Promise<string> {
  if (!_refreshPromise) {
    const url = `${BASE}/api/v1/auth/token/refresh/`

    _refreshPromise = axios
      .post<{ access: string }>(url, {}, { withCredentials: true })
      .then(({ data }) => data.access)
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
