import { apiClient } from './client'

export interface QuotationItem {
  id: string
  quotation_id: string
  product_id: string | null
  description: string
  quantity: string
  unit: string
  unit_price: string
  discount_rate: string
  tax_rate: string
  sort_order: number
  subtotal: string
  discount_amount: string
  tax_amount: string
  line_total: string
  created_at: string
  updated_at: string
}

export interface Quotation {
  id: string
  organization_id: string
  created_by: string
  quotation_number: string
  status: string

  customer_id: string
  issue_date: string
  expiry_date: string

  currency: string
  notes: string | null
  terms: string | null

  subtotal: string
  discount_amount: string
  tax_amount: string
  total_amount: string

  items: QuotationItem[]

  created_at: string
  updated_at: string
}

export interface QuotationListResponse {
  items: Quotation[]
  total: number
  page: number
  page_size: number
}

export interface QuotationItemCreate {
  product_id?: string | null
  description: string
  quantity: number
  unit: string
  unit_price: number
  discount_rate: number
  tax_rate: number
  sort_order: number
}

export interface QuotationCreate {
  customer_id: string
  issue_date: string
  expiry_date: string
  currency: string
  notes?: string | null
  terms?: string | null
  items: QuotationItemCreate[]
}

export async function getQuotations(
  page = 1,
  pageSize = 20,
  search?: string,
): Promise<QuotationListResponse> {
  const response = await apiClient.get<QuotationListResponse>(
    '/v1/quotations',
    {
      params: {
        page,
        page_size: pageSize,
        search: search || undefined,
      },
    },
  )

  return response.data
}

export async function createQuotation(
  data: QuotationCreate,
): Promise<Quotation> {
  const response = await apiClient.post<Quotation>(
    '/v1/quotations',
    data,
  )

  return response.data
}

export async function getQuotation(
  quotationId: string,
): Promise<Quotation> {
  const response = await apiClient.get<Quotation>(
    `/v1/quotations/${quotationId}`,
  )

  return response.data
}

export async function deleteQuotation(
  quotationId: string,
): Promise<void> {
  await apiClient.delete(
    `/v1/quotations/${quotationId}`,
  )
}

export async function downloadQuotationPdf(
  quotationId: string,
  quotationNumber: string,
): Promise<void> {
  const response = await apiClient.get(
    `/v1/quotations/${quotationId}/pdf`,
    {
      responseType: 'blob',
    },
  )

  const url = window.URL.createObjectURL(
    new Blob([response.data], {
      type: 'application/pdf',
    }),
  )

  const link = document.createElement('a')

  link.href = url
  link.download = `${quotationNumber}.pdf`

  document.body.appendChild(link)
  link.click()
  link.remove()

  window.URL.revokeObjectURL(url)
}