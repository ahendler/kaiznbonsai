import type { OrderStatus } from '@/api/orders'

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
