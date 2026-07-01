import api from './client'
import type { PaginatedResponse } from './inventory'
import type { FinancialPeriodParams } from '@/utils/financialPeriod'

export type MovementReason = 'RECEIPT' | 'SALE' | 'RETURN' | 'ADJUSTMENT'

export interface MovementOrderRef {
  id: number
  title: string
  status: 'DRAFT' | 'CONFIRMED' | 'CANCELLED'
}

export interface StockMovementListItem {
  id: string
  created_at: string
  reason: MovementReason
  delta: string
  product: {
    id: number
    name: string
    sku: string
    unit_of_measure: 'KG' | 'G' | 'L' | 'ML' | 'UNIT'
  }
  stock_batch: {
    id: string
    lot_code: string
  }
  sales_order: MovementOrderRef | null
  purchase_order: MovementOrderRef | null
}

export interface StockMovementListFilters extends FinancialPeriodParams {
  reason?: MovementReason[]
  product?: number
  stock_batch?: string
  search?: string
}

function buildMovementQueryParams(
  filters: StockMovementListFilters,
  cursor: string | null,
): Record<string, string> {
  const params: Record<string, string> = {}
  if (cursor) {
    params.cursor = cursor
  }
  if (filters.from && filters.to) {
    params.from = filters.from
    params.to = filters.to
  }
  if (filters.reason?.length) {
    params.reason = filters.reason.join(',')
  }
  if (filters.product !== undefined) {
    params.product = String(filters.product)
  }
  if (filters.stock_batch) {
    params.stock_batch = filters.stock_batch
  }
  const search = filters.search?.trim()
  if (search) {
    params.search = search
  }
  return params
}

export function stockMovementQueryKey(filters: StockMovementListFilters): unknown[] {
  return [
    'stock-movements',
    'infinite',
    filters.from ?? null,
    filters.to ?? null,
    filters.reason?.join(',') ?? null,
    filters.product ?? null,
    filters.stock_batch ?? null,
    filters.search?.trim() || null,
  ]
}

export async function listStockMovements(
  cursor: string | null = null,
  filters: StockMovementListFilters = {},
): Promise<PaginatedResponse<StockMovementListItem>> {
  const response = await api.get('/inventory/movements/', {
    params: buildMovementQueryParams(filters, cursor),
  })
  return response.data
}

export async function listStockBatchMovements(
  stockBatchId: string,
  cursor: string | null = null,
): Promise<PaginatedResponse<StockMovementListItem>> {
  const params: Record<string, string> = {}
  if (cursor) {
    params.cursor = cursor
  }
  const response = await api.get(`/inventory/stocks/${stockBatchId}/movements/`, { params })
  return response.data
}
