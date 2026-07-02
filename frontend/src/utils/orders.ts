import type { OrderStatus, StockAllocationStrategy } from '@/api/orders'

export type OrderKind = 'purchases' | 'sales'

export type OrderStatusSlug = 'draft' | 'confirmed' | 'cancelled'

export type OrderPathQuery = {
  status?: OrderStatusSlug
}

const ORDER_STATUS_SLUGS: readonly OrderStatusSlug[] = ['draft', 'confirmed', 'cancelled']

export type OrderStatusFilter = 'all' | OrderStatusSlug

export const ORDER_STATUS_FILTER_OPTIONS = [
  { value: 'all', label: 'All statuses' },
  { value: 'draft', label: 'Draft only' },
  { value: 'confirmed', label: 'Confirmed only' },
  { value: 'cancelled', label: 'Cancelled only' },
] as const satisfies ReadonlyArray<{ value: OrderStatusFilter; label: string }>

export function parseOrderStatusSlug(value: string | null): OrderStatusSlug | null {
  if (!value) return null
  const normalized = value.toLowerCase()
  return ORDER_STATUS_SLUGS.includes(normalized as OrderStatusSlug)
    ? (normalized as OrderStatusSlug)
    : null
}

export function orderStatusSlugToApi(slug: OrderStatusSlug): OrderStatus {
  return slug.toUpperCase() as OrderStatus
}

export function orderStatusToSlug(status: OrderStatus): OrderStatusSlug {
  return status.toLowerCase() as OrderStatusSlug
}

export function parseOrderStatusFilter(value: string | null): OrderStatusFilter {
  const slug = parseOrderStatusSlug(value)
  return slug ?? 'all'
}

export function buildOrderPath(
  kind: OrderKind,
  orderId?: number,
  query?: OrderPathQuery,
): string {
  const base = kind === 'sales' ? '/orders/sales' : '/orders/purchases'
  const params = new URLSearchParams()
  if (query?.status) params.set('status', query.status)
  if (orderId != null) params.set('orderId', String(orderId))
  const qs = params.toString()
  return qs ? `${base}?${qs}` : base
}

export function parseOrderId(value: string | null): number | null {
  if (!value) return null
  const id = Number.parseInt(value, 10)
  if (!Number.isFinite(id) || id <= 0) return null
  return id
}

export const ALLOCATION_OPTIONS = [
  {
    value: 'FIFO' as const,
    label: 'Oldest stock first',
    description: 'Deduct from batches received earliest.',
  },
  {
    value: 'FEFO' as const,
    label: 'Expiring soonest',
    description: 'Deduct from batches with the nearest best-before date. Lots without a date are used last.',
  },
] satisfies ReadonlyArray<{
  value: StockAllocationStrategy
  label: string
  description: string
}>

export const DEFAULT_ALLOCATION_STRATEGY: StockAllocationStrategy = 'FIFO'

export function getAllocationDescription(strategy: StockAllocationStrategy): string {
  return ALLOCATION_OPTIONS.find((option) => option.value === strategy)?.description ?? ''
}

export function orderStatusColor(status: OrderStatus): string {
  if (status === 'CONFIRMED') return 'green'
  if (status === 'CANCELLED') return 'red'
  return 'yellow'
}

export function lineTotal(quantity: string, unitPrice: string): number {
  return parseFloat(quantity) * parseFloat(unitPrice)
}

export function sumLineTotals(items: Array<{ quantity: string; unit_cost?: string; unit_price?: string }>, priceField: 'unit_cost' | 'unit_price'): number {
  return items.reduce((sum, item) => {
    const unitValue = item[priceField]
    if (!unitValue) return sum
    return sum + lineTotal(item.quantity, unitValue)
  }, 0)
}

export function formatOrderMoney(amount: number): string {
  return `$${amount.toFixed(2)}`
}

export function getPurchaseOrderCancelTooltip(status: OrderStatus): string {
  return status === 'DRAFT' ? 'Cancel draft order' : 'Cancel order (removes stock batches)'
}

export function getPurchaseOrderCancelDescription(status: OrderStatus): string {
  if (status === 'DRAFT') {
    return 'This will cancel the draft order. No stock has been received yet.'
  }
  return 'This will attempt to remove the generated stock batches. It cannot be undone if the stock has already been consumed.'
}

export function getSalesOrderCancelTooltip(status: OrderStatus): string {
  return status === 'DRAFT' ? 'Cancel draft order' : 'Cancel order (refunds stock)'
}

export function getSalesOrderCancelDescription(status: OrderStatus): string {
  if (status === 'DRAFT') {
    return 'This will cancel the draft order. No stock has been deducted yet.'
  }
  return 'This will attempt to refund the deducted stock back to your inventory.'
}
