export function formatCurrency(val: string | number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(Number(val))
}

export function getMarginColor(margin: string | number): 'green' | 'yellow' | 'red' {
  const marginNum = Number(margin)
  if (marginNum < 0) return 'red'
  if (marginNum < 20) return 'red'
  if (marginNum < 40) return 'yellow'
  return 'green'
}

/** Clamp margin to 0–100 for progress bars; negative margins return null (no bar). */
export function getMarginProgressValue(margin: string | number): number | null {
  const marginNum = Number(margin)
  if (marginNum < 0) return null
  return Math.min(marginNum, 100)
}

function formatPercent(value: string | number | null | undefined, nullable = false): string {
  if (nullable && (value === null || value === undefined || value === '')) {
    return '—'
  }
  return `${Number(value).toFixed(1)}%`
}

export function formatMarginPercent(margin: string | number): string {
  return formatPercent(margin)
}

export function formatMarkupPercent(markup: string | number | null | undefined): string {
  return formatPercent(markup, true)
}

export function formatQuantity(qty: string | number): string {
  const n = Number(qty)
  if (Number.isInteger(n)) return String(n)
  return n.toFixed(3).replace(/\.?0+$/, '')
}
