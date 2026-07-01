import type { MovementReason, StockMovementListItem } from '@/api/activity'
import { buildOrderPath } from '@/utils/orders'
import { formatQuantity } from '@/utils/financials'

export const MOVEMENT_REASON_OPTIONS = [
  { value: 'RECEIPT' as const, label: 'Stock received' },
  { value: 'SALE' as const, label: 'Sold' },
  { value: 'RETURN' as const, label: 'Sale reversed' },
  { value: 'ADJUSTMENT' as const, label: 'Quantity corrected' },
  { value: 'VOID' as const, label: 'Batch voided' },
  { value: 'RECEIPT_REVERSAL' as const, label: 'Receipt reversed' },
] satisfies ReadonlyArray<{ value: MovementReason; label: string }>

const MOVEMENT_LABELS: Record<MovementReason, string> = {
  RECEIPT: 'Stock received',
  SALE: 'Sold',
  RETURN: 'Sale reversed',
  ADJUSTMENT: 'Quantity corrected',
  VOID: 'Batch voided',
  RECEIPT_REVERSAL: 'Receipt reversed',
}

export function getMovementLabel(reason: MovementReason): string {
  return MOVEMENT_LABELS[reason]
}

export function formatSignedDelta(delta: string, unit: string): string {
  const n = Number(delta)
  const sign = n >= 0 ? '+' : '−'
  const qty = formatQuantity(Math.abs(n))
  return `${sign}${qty} ${unit}`
}

export function getDeltaColor(delta: string): 'green' | 'red' {
  return Number(delta) >= 0 ? 'green' : 'red'
}

export function getMovementReference(movement: StockMovementListItem): string {
  if (movement.sales_order?.title) {
    return movement.sales_order.title
  }
  if (movement.sales_order) {
    return `Sales order #${movement.sales_order.id}`
  }
  if (movement.purchase_order?.title) {
    return movement.purchase_order.title
  }
  if (movement.purchase_order) {
    return `Purchase order #${movement.purchase_order.id}`
  }
  if (movement.reason === 'ADJUSTMENT') {
    return 'Manual correction'
  }
  if (movement.reason === 'RECEIPT') {
    return 'Manual entry'
  }
  if (movement.reason === 'VOID') {
    return 'Batch voided'
  }
  return '—'
}

export function formatBatchLabel(lotCode: string, batchId: string): string {
  if (lotCode.trim()) {
    return lotCode
  }
  return batchId.slice(0, 8)
}

export function getOrderDetailPath(movement: StockMovementListItem): string | null {
  if (movement.sales_order) {
    return buildOrderPath('sales', movement.sales_order.id)
  }
  if (movement.purchase_order) {
    return buildOrderPath('purchases', movement.purchase_order.id)
  }
  return null
}
