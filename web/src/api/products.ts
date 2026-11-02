import { apiClient } from './client'

export interface Product {
  id: string
  organization_id: string
  sku: string
  name: string
  description: string | null
  unit: string
  unit_price: string
  currency: string
  tax_rate: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ProductCreate {
  sku: string
  name: string
  description?: string | null
  unit: string
  unit_price: number
  currency: string
  tax_rate: number
}

export interface ProductListResponse {
  items: Product[]
  total: number
  page: number
  page_size: number
}

export async function getProducts(
  search = '',
): Promise<ProductListResponse> {
  const response =
    await apiClient.get<ProductListResponse>(
      '/v1/products',
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

export async function getProduct(
  id: string,
): Promise<Product> {
  const response =
    await apiClient.get<Product>(
      `/v1/products/${id}`,
    )

  return response.data
}

export async function createProduct(
  data: ProductCreate,
): Promise<Product> {
  const response =
    await apiClient.post<Product>(
      '/v1/products',
      data,
    )

  return response.data
}

export async function updateProduct(
  id: string,
  data: Partial<ProductCreate>,
): Promise<Product> {
  const response =
    await apiClient.put<Product>(
      `/v1/products/${id}`,
      data,
    )

  return response.data
}

export async function deleteProduct(
  id: string,
): Promise<void> {
  await apiClient.delete(
    `/v1/products/${id}`,
  )
}