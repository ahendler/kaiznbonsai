export interface User {
  id: number
  email: string
  first_name: string
  last_name: string
}

export interface AuthTokens {
  access: string
  user: User
}
