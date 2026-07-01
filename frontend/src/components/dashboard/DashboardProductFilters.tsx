import { Group, Select, TextInput } from '@mantine/core'
import { IconSearch } from '@tabler/icons-react'
import type { ActivityFilter, MarginBand, ProductFinancialOrdering } from '@/api/financials'

const ACTIVITY_FILTER_OPTIONS = [
  { value: 'all', label: 'All products' },
  { value: 'movement', label: 'With activity' },
  { value: 'stale', label: 'No activity' },
] as const

const MARGIN_BAND_OPTIONS = [
  { value: 'negative', label: 'Negative margin' },
  { value: 'low', label: 'Low (< 20%)' },
  { value: 'medium', label: 'Medium (20–40%)' },
  { value: 'high', label: 'High (≥ 40%)' },
] as const

const ORDERING_OPTIONS = [
  { value: '-revenue', label: 'Revenue (high → low)' },
  { value: '-profit', label: 'Profit (high → low)' },
  { value: '-margin', label: 'Gross margin (high → low)' },
  { value: '-markup_on_cost', label: 'Markup (high → low)' },
  { value: 'name', label: 'Name (A → Z)' },
  { value: '-created_at', label: 'Recently added' },
] as const

interface DashboardProductFiltersProps {
  search: string
  onSearchChange: (value: string) => void
  activityFilter: ActivityFilter
  onActivityFilterChange: (value: ActivityFilter) => void
  marginBand: MarginBand | null
  onMarginBandChange: (value: MarginBand | null) => void
  ordering: ProductFinancialOrdering
  onOrderingChange: (value: ProductFinancialOrdering) => void
}

export default function DashboardProductFilters({
  search,
  onSearchChange,
  activityFilter,
  onActivityFilterChange,
  marginBand,
  onMarginBandChange,
  ordering,
  onOrderingChange,
}: DashboardProductFiltersProps) {
  return (
    <Group align="flex-end" wrap="wrap" gap="md">
      <TextInput
        className="min-w-[220px] flex-1"
        placeholder="Search by name or SKU"
        leftSection={<IconSearch size={16} />}
        value={search}
        onChange={(e) => onSearchChange(e.currentTarget.value)}
      />
      <Select
        className="w-[220px]"
        data={[...ACTIVITY_FILTER_OPTIONS]}
        value={activityFilter}
        onChange={(value) => onActivityFilterChange((value as ActivityFilter | null) ?? 'all')}
        allowDeselect={false}
      />
      <Select
        className="w-[220px]"
        placeholder="All gross margins"
        clearable
        data={[...MARGIN_BAND_OPTIONS]}
        value={marginBand}
        onChange={(value) => onMarginBandChange(value as MarginBand | null)}
      />
      <Select
        className="w-[200px]"
        data={[...ORDERING_OPTIONS]}
        value={ordering}
        onChange={(value) => onOrderingChange((value as ProductFinancialOrdering | null) ?? '-created_at')}
        allowDeselect={false}
      />
    </Group>
  )
}
