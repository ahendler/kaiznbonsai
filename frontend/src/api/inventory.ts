import api from './client'

// ----------------------------------------------------------------------------
// Interfaces
// ----------------------------------------------------------------------------

export interface PaginatedResponse<T> {
  next: string | null
  previous: string | null
  results: T[]
}

export interface Product {
  id: string
  name: string
  sku: string
  description: string
  unit_of_measure: 'KG' | 'G' | 'L' | 'ML' | 'UNIT'
  total_stock: string // Decimal returned as string from DRF
  has_stock_batches: boolean
  has_voided_batches: boolean
  created_at: string
  updated_at: string
}

export interface ProductCreatePayload {
  name: string
  sku: string
  description?: string
  unit_of_measure: 'KG' | 'G' | 'L' | 'ML' | 'UNIT'
}

export type ProductUpdatePayload = Partial<ProductCreatePayload>

export interface ProductListFilters {
  search?: string
  unit_of_measure?: Product['unit_of_measure'][]
  in_stock?: boolean
}

export interface Stock {
  id: string
  product: string // UUID
  lot_code: string
  initial_quantity: string // Decimal
  current_quantity: string // Decimal
  unit_cost: string // Decimal
  best_before: string | null // Date (YYYY-MM-DD)
  voided_at: string | null
  is_po_linked: boolean
  created_at: string
  updated_at: string
}

export interface StockCreatePayload {
  product: string
  lot_code?: string
  initial_quantity: string
  current_quantity: string
  unit_cost: string
  best_before?: string | null
}

export interface StockUpdatePayload {
  lot_code?: string
  initial_quantity?: string
  current_quantity?: string
  unit_cost?: string
  best_before?: string | null
}

// ----------------------------------------------------------------------------
// Products API
// ----------------------------------------------------------------------------

export const listProducts = async (
  cursor: string | null = null,
  filters: ProductListFilters = {},
): Promise<PaginatedResponse<Product>> => {
  const params: Record<string, string> = {}
  if (cursor) {
    params.cursor = cursor
  }
  const search = filters.search?.trim()
  if (search) {
    params.search = search
  }
  if (filters.unit_of_measure?.length) {
    params.unit_of_measure = filters.unit_of_measure.join(',')
  }
  if (filters.in_stock === true) {
    params.in_stock = 'true'
  } else if (filters.in_stock === false) {
    params.in_stock = 'false'
  }
  const response = await api.get('/inventory/products/', { params })
  return response.data
}

export const createProduct = async (payload: ProductCreatePayload): Promise<Product> => {
  const response = await api.post('/inventory/products/', payload)
  return response.data
}

export const updateProduct = async (id: string, payload: ProductUpdatePayload): Promise<Product> => {
  const response = await api.patch(`/inventory/products/${id}/`, payload)
  return response.data
}

export const deleteProduct = async (id: string): Promise<void> => {
  await api.delete(`/inventory/products/${id}/`)
}

// ----------------------------------------------------------------------------
// Stocks API
// ----------------------------------------------------------------------------

export interface StockListOptions {
  include_voided?: boolean
}

export const listStocks = async (
  productId: string,
  cursor: string | null = null,
  options: StockListOptions = {},
): Promise<PaginatedResponse<Stock>> => {
  const params: Record<string, string> = { product: productId }
  if (cursor) {
    params.cursor = cursor
  }
  if (options.include_voided) {
    params.include_voided = 'true'
  }
  const response = await api.get('/inventory/stocks/', { params })
  return response.data
}

export const createStock = async (payload: StockCreatePayload): Promise<Stock> => {
  const response = await api.post('/inventory/stocks/', payload)
  return response.data
}

export const updateStock = async (id: string, payload: StockUpdatePayload): Promise<Stock> => {
  const response = await api.patch(`/inventory/stocks/${id}/`, payload)
  return response.data
}

export const voidStock = async (id: string): Promise<Stock> => {
  const response = await api.post(`/inventory/stocks/${id}/void/`)
  return response.data
}
