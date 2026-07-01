import dayjs from 'dayjs'
import quarterOfYear from 'dayjs/plugin/quarterOfYear'

dayjs.extend(quarterOfYear)

export type FinancialPeriodPreset =
  | 'all_time'
  | 'this_month'
  | 'last_month'
  | 'this_quarter'
  | 'year_to_date'
  | 'custom'

export interface FinancialPeriod {
  preset: FinancialPeriodPreset
  from: string | null
  to: string | null
}

export interface FinancialPeriodParams {
  from?: string
  to?: string
}

export const DEFAULT_FINANCIAL_PERIOD: FinancialPeriod = {
  preset: 'all_time',
  from: null,
  to: null,
}

export const FINANCIAL_PERIOD_PRESETS = [
  { value: 'all_time', label: 'All time' },
  { value: 'this_month', label: 'This month' },
  { value: 'last_month', label: 'Last month' },
  { value: 'this_quarter', label: 'This quarter' },
  { value: 'year_to_date', label: 'Year to date' },
  { value: 'custom', label: 'Custom range' },
] as const

export function formatPeriodDate(value: dayjs.Dayjs | Date): string {
  return dayjs(value).format('YYYY-MM-DD')
}

export function resolveFinancialPeriod(preset: FinancialPeriodPreset): FinancialPeriod {
  const today = dayjs().startOf('day')

  switch (preset) {
    case 'all_time':
      return { preset, from: null, to: null }
    case 'this_month':
      return {
        preset,
        from: formatPeriodDate(today.startOf('month')),
        to: formatPeriodDate(today),
      }
    case 'last_month': {
      const lastMonth = today.subtract(1, 'month')
      return {
        preset,
        from: formatPeriodDate(lastMonth.startOf('month')),
        to: formatPeriodDate(lastMonth.endOf('month')),
      }
    }
    case 'this_quarter':
      return {
        preset,
        from: formatPeriodDate(today.startOf('quarter')),
        to: formatPeriodDate(today),
      }
    case 'year_to_date':
      return {
        preset,
        from: formatPeriodDate(today.startOf('year')),
        to: formatPeriodDate(today),
      }
    case 'custom':
      return { preset, from: null, to: null }
    default:
      return DEFAULT_FINANCIAL_PERIOD
  }
}

export function customFinancialPeriod(from: Date | null, to: Date | null): FinancialPeriod {
  if (!from || !to) {
    return { preset: 'custom', from: null, to: null }
  }

  const start = dayjs(from).startOf('day')
  const end = dayjs(to).startOf('day')
  const [rangeStart, rangeEnd] = start.isAfter(end) ? [end, start] : [start, end]

  return {
    preset: 'custom',
    from: formatPeriodDate(rangeStart),
    to: formatPeriodDate(rangeEnd),
  }
}

export function toFinancialPeriodParams(period: FinancialPeriod): FinancialPeriodParams {
  if (period.from && period.to) {
    return { from: period.from, to: period.to }
  }
  return {}
}

export function formatFinancialPeriodLabel(period: FinancialPeriod): string | null {
  if (period.preset === 'all_time' || !period.from || !period.to) {
    return null
  }

  const from = dayjs(period.from)
  const to = dayjs(period.to)

  if (from.isSame(to, 'day')) {
    return from.format('MMM D, YYYY')
  }

  if (from.year() === to.year()) {
    return `${from.format('MMM D')} – ${to.format('MMM D, YYYY')}`
  }

  return `${from.format('MMM D, YYYY')} – ${to.format('MMM D, YYYY')}`
}

export function isFinancialPeriodActive(period: FinancialPeriod): boolean {
  return period.preset !== 'all_time' && period.from !== null && period.to !== null
}
