import type { OrderStatus, StockAllocationStrategy } from '@/api/orders'

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
