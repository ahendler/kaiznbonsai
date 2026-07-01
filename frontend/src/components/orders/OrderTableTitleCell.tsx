import { useRef, useState } from 'react'
import { Text, Tooltip } from '@mantine/core'

/** Max width for the Name column — truncation happens at the cell edge, not before. */
export const ORDER_NAME_COLUMN_MAX_WIDTH = 320

interface OrderTableTitleCellProps {
  title?: string | null
}

export function OrderTableTitleCell({ title }: OrderTableTitleCellProps) {
  const ref = useRef<HTMLDivElement>(null)
  const [showTooltip, setShowTooltip] = useState(false)
  const trimmed = title?.trim()

  if (!trimmed) {
    return <Text c="dimmed">—</Text>
  }

  return (
    <Tooltip label={trimmed} disabled={!showTooltip} multiline maw={300}>
      <Text
        ref={ref}
        component="div"
        truncate="end"
        w="100%"
        style={{ minWidth: 0 }}
        onMouseEnter={() => {
          if (ref.current) {
            setShowTooltip(ref.current.scrollWidth > ref.current.clientWidth)
          }
        }}
      >
        {trimmed}
      </Text>
    </Tooltip>
  )
}
