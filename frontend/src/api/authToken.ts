let accessToken: string | null = null
let onAccessTokenRefreshed: ((token: string) => void) | null = null

export function setAccessToken(token: string | null): void {
  accessToken = token
}

export function getAccessToken(): string | null {
  return accessToken
}

/** Called after a silent refresh so axios and React auth state stay in sync. */
export function persistRefreshedAccessToken(token: string): void {
  accessToken = token
  onAccessTokenRefreshed?.(token)
}

export function registerOnAccessTokenRefreshed(
  callback: (token: string) => void,
): () => void {
  onAccessTokenRefreshed = callback
  return () => {
    if (onAccessTokenRefreshed === callback) {
      onAccessTokenRefreshed = null
    }
  }
}
