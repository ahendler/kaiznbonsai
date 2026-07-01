import { ActionIcon, Badge, Group, Text, Tooltip } from '@mantine/core'
import { IconExternalLink } from '@tabler/icons-react'
import { Link } from 'react-router-dom'
import type { OrderStatus } from '@/api/orders'
import { orderStatusColor } from '@/utils/orders'

interface OrderReferenceCellProps {
  reference: string
  orderPath: string | null
  orderStatus?: OrderStatus | null
  textSize?: 'xs' | 'sm'
}

export default function OrderReferenceCell({
  reference,
  orderPath,
  orderStatus,
  textSize = 'sm',
}: OrderReferenceCellProps) {
  return (
    <Group gap="xs" wrap="nowrap">
      <Text size={textSize}>{reference}</Text>
      {orderPath && (
        <Tooltip label="Open order in new tab">
          <ActionIcon
            component={Link}
            to={orderPath}
            target="_blank"
            rel="noopener noreferrer"
            variant="subtle"
            size="sm"
            color="gray"
            aria-label="Open order in new tab"
          >
            <IconExternalLink size={14} />
          </ActionIcon>
        </Tooltip>
      )}
      {orderStatus && (
        <Badge size="xs" color={orderStatusColor(orderStatus)} variant="light">
          {orderStatus}
        </Badge>
      )}
    </Group>
  )
}
