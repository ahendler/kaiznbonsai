import axios from 'axios'
import { getAccessToken } from '@/context/AuthContext'
import { getOrStartRefresh } from '@/api/authRefresh'

const BASE = import.meta.env.VITE_API_URL ?? ''

const api = axios.create({
  baseURL: `${BASE}/api/v1`,
  withCredentials: true,
})

// Attach the access token to every outgoing request.
api.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// On a 401, attempt a silent refresh and replay the original request.
// If multiple requests fail simultaneously, they are held in a queue and
// replayed together once the single refresh call resolves.
let isRefreshing = false
let pendingQueue: Array<(token: string) => void> = []

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config

    if (error.response?.status === 401 && !original._retry) {
      if (isRefreshing) {
        return new Promise((resolve) => {
          pendingQueue.push((token) => {
            original.headers.Authorization = `Bearer ${token}`
            resolve(api(original))
          })
        })
      }

      original._retry = true
      isRefreshing = true

      try {
        const newToken = await getOrStartRefresh()
        pendingQueue.forEach((cb) => cb(newToken))
        pendingQueue = []
        original.headers.Authorization = `Bearer ${newToken}`
        return api(original)
      } catch {
        pendingQueue = []
        // Redirect to login — refresh token is gone or expired.
        window.location.href = '/login'
        return Promise.reject(error)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  },
)

export default api
