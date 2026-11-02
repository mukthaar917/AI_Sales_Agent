import { apiClient } from './client'

export interface Customer {
  id: string
  organization_id: string
  company_name: string
  contact_name: string | null
  email: string | null
  phone: string | null
  website: string | null
  address: string | null
  city: string | null
  state: string | null
  country: string | null
  postal_code: string | null
  tax_number: string | null
  notes: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface CustomerCreate {
  company_name: string
  contact_name?: string | null
  email?: string | null
  phone?: string | null
  website?: string | null
  address?: string | null
  city?: string | null
  state?: string | null
  country?: string | null
  postal_code?: string | null
  tax_number?: string | null
  notes?: string | null
}

export interface CustomerListResponse {
  items: Customer[]
  total: number
  page: number
  page_size: number
}

export async function getCustomers(
  search = '',
): Promise<CustomerListResponse> {
  const response =
    await apiClient.get<CustomerListResponse>(
      '/v1/customers',
      {
        params: {
          page: 1,
          page_size: 100,
          search: search || undefined,
        },
      },
    )

  return response.data
}

export async function getCustomer(
  id: string,
): Promise<Customer> {
  const response =
    await apiClient.get<Customer>(
      `/v1/customers/${id}`,
    )

  return response.data
}

export async function createCustomer(
  data: CustomerCreate,
): Promise<Customer> {
  const response =
    await apiClient.post<Customer>(
      '/v1/customers',
      data,
    )

  return response.data
}

export async function updateCustomer(
  id: string,
  data: Partial<CustomerCreate>,
): Promise<Customer> {
  const response =
    await apiClient.put<Customer>(
      `/v1/customers/${id}`,
      data,
    )

  return response.data
}

export async function deleteCustomer(
  id: string,
): Promise<void> {
  await apiClient.delete(
    `/v1/customers/${id}`,
  )
}