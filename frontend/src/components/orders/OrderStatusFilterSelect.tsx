import { Select } from '@mantine/core'
import { ORDER_STATUS_FILTER_OPTIONS, type OrderStatusFilter } from '@/utils/orders'

interface Props {
  value: OrderStatusFilter
  onChange: (value: OrderStatusFilter) => void
}

export function OrderStatusFilterSelect({ value, onChange }: Props) {
  return (
    <Select
      className="w-[200px]"
      data={[...ORDER_STATUS_FILTER_OPTIONS]}
      value={value}
      onChange={(next) => onChange((next as OrderStatusFilter | null) ?? 'all')}
    />
  )
}
