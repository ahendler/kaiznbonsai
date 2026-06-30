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

export function getFormErrorsFromApi(data: unknown): Record<string, string> | null {
  if (!data || typeof data !== 'object' || Array.isArray(data)) {
    return null
  }

  const record = data as Record<string, unknown>
  const errors: Record<string, string> = {}

  for (const [key, value] of Object.entries(record)) {
    if (key === 'detail') continue

    if (key === 'items_data') {
      if (typeof value === 'string') {
        errors.items = value
        continue
      }
      if (Array.isArray(value)) {
        value.forEach((itemErrors, index) => {
          if (!itemErrors || typeof itemErrors !== 'object' || Array.isArray(itemErrors)) {
            return
          }
          for (const [field, msgs] of Object.entries(itemErrors as Record<string, unknown>)) {
            const message = Array.isArray(msgs) ? msgs[0] : msgs
            if (message != null) {
              errors[`items.${index}.${field}`] = String(message)
            }
          }
        })
        continue
      }
    }

    if (Array.isArray(value) && value.length > 0) {
      errors[key] = String(value[0])
    } else if (typeof value === 'string') {
      errors[key] = value
    }
  }

  return Object.keys(errors).length > 0 ? errors : null
}

export function applyApiFieldErrors(
  form: { setErrors: (errors: Record<string, string>) => void },
  error: unknown,
): boolean {
  const errors = getFormErrorsFromApi(getAxiosResponseData(error))
  if (!errors) return false
  form.setErrors(errors)
  return true
}
