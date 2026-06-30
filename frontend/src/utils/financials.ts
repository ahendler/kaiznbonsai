export function formatCurrency(val: string | number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(Number(val))
}

export function getMarginColor(margin: string | number): 'green' | 'yellow' | 'red' {
  const marginNum = Number(margin)
  if (marginNum < 20) return 'red'
  if (marginNum < 40) return 'yellow'
  return 'green'
}

export function formatMarginPercent(margin: string | number): string {
  return `${Number(margin).toFixed(1)}%`
}

export function formatQuantity(qty: string | number): string {
  const n = Number(qty)
  if (Number.isInteger(n)) return String(n)
  return n.toFixed(3).replace(/\.?0+$/, '')
}
