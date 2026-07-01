import { useEffect, useState } from 'react'
import { Group, Select } from '@mantine/core'
import { DatePickerInput } from '@mantine/dates'
import {
  customFinancialPeriod,
  FINANCIAL_PERIOD_PRESETS,
  type FinancialPeriod,
  type FinancialPeriodPreset,
  resolveFinancialPeriod,
} from '@/utils/financialPeriod'

interface FinancialPeriodFilterProps {
  value: FinancialPeriod
  onChange: (period: FinancialPeriod) => void
}

function toDraftRange(period: FinancialPeriod): [Date | null, Date | null] {
  if (!period.from || !period.to) {
    return [null, null]
  }
  return [
    new Date(`${period.from}T12:00:00`),
    new Date(`${period.to}T12:00:00`),
  ]
}

export default function FinancialPeriodFilter({ value, onChange }: FinancialPeriodFilterProps) {
  const [draftRange, setDraftRange] = useState<[Date | null, Date | null]>(() => toDraftRange(value))

  useEffect(() => {
    if (value.preset !== 'custom') {
      setDraftRange([null, null])
      return
    }
    if (value.from && value.to) {
      setDraftRange(toDraftRange(value))
    }
  }, [value.preset, value.from, value.to])

  const handlePresetChange = (next: string | null) => {
    if (!next) return
    onChange(resolveFinancialPeriod(next as FinancialPeriodPreset))
  }

  const handleRangeChange = (range: [Date | null, Date | null]) => {
    setDraftRange(range)

    if (range[0] && range[1]) {
      onChange(customFinancialPeriod(range[0], range[1]))
      return
    }

    if (!range[0] && !range[1]) {
      onChange({ preset: 'custom', from: null, to: null })
    }
  }

  return (
    <Group align="center" gap="sm" wrap="nowrap">
      <Select
        aria-label="Financial period"
        data={[...FINANCIAL_PERIOD_PRESETS]}
        value={value.preset}
        onChange={handlePresetChange}
        w={160}
        flex="0 0 auto"
        allowDeselect={false}
      />
      {value.preset === 'custom' && (
        <DatePickerInput
          type="range"
          aria-label="Custom date range"
          placeholder="Pick dates"
          value={draftRange}
          onChange={handleRangeChange}
          w={300}
          miw={300}
          flex="0 0 auto"
          maxDate={new Date()}
          clearable
        />
      )}
    </Group>
  )
}
