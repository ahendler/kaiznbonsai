import { isAxiosError } from 'axios'

export function getApiErrorMessage(error: unknown, fallback = 'Something went wrong'): string {
  if (isAxiosError(error)) {
    const data = error.response?.data
    if (typeof data === 'string') return data
    if (Array.isArray(data) && data.length > 0) return String(data[0])
    if (data && typeof data === 'object' && 'detail' in data) {
      const detail = (data as { detail: unknown }).detail
      if (typeof detail === 'string') return detail
    }
    if (error.message) return error.message
  }
  if (error instanceof Error) return error.message
  return fallback
}

export function getAxiosResponseData(error: unknown): unknown {
  if (isAxiosError(error)) {
    return error.response?.data
  }
  return undefined
}
