import { apiClient } from './client'

export interface LoginResponse {
  access_token: string
  token_type: string
}

export interface CurrentUser {
  id: string
  organization_id: string
  email: string
  full_name: string
  role: string
  is_active: boolean
}

export async function login(
  email: string,
  password: string,
): Promise<LoginResponse> {
  const formData = new URLSearchParams()
  formData.append('username', email)
  formData.append('password', password)

  const response = await apiClient.post<LoginResponse>(
    '/auth/login',
    formData,
    {
      headers: {
        'Content-Type':
          'application/x-www-form-urlencoded',
      },
    },
  )

  return response.data
}

export async function getCurrentUser(): Promise<CurrentUser> {
  const response =
    await apiClient.get<CurrentUser>('/auth/me')

  return response.data
}