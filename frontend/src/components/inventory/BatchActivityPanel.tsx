import { Anchor, Badge, Center, Group, Loader, Stack, Table, Text } from '@mantine/core'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { listStockBatchMovements } from '@/api/activity'
import OrderReferenceCell from '@/components/orders/OrderReferenceCell'
import {
  formatSignedDelta,
  getDeltaColor,
  getMovementLabel,
  getMovementReference,
  getOrderDetailPath,
} from '@/utils/activity'

const BATCH_ACTIVITY_LIMIT = 10

interface BatchActivityPanelProps {
  batchId: string
}

export default function BatchActivityPanel({ batchId }: BatchActivityPanelProps) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['stock-batch-movements', batchId],
    queryFn: () => listStockBatchMovements(batchId),
    enabled: !!batchId,
  })

  const movements = (data?.results ?? []).slice(0, BATCH_ACTIVITY_LIMIT)

  if (isLoading) {
    return (
      <Center py="md">
        <Loader size="sm" />
      </Center>
    )
  }

  if (isError) {
    return (
      <Text size="sm" c="red" py="sm" px="md">
        Could not load activity for this batch.
      </Text>
    )
  }

  return (
    <Stack gap="xs" py="sm" px="md" className="bg-[var(--mantine-color-gray-0)]">
      <Group justify="space-between" wrap="nowrap">
        <Text size="sm" fw={500}>Activity on this batch</Text>
        <Anchor component={Link} to={`/history?stock_batch=${batchId}`} size="sm">
          View all in Stock History
        </Anchor>
      </Group>

      {movements.length === 0 ? (
        <Text size="sm" c="dimmed">No activity recorded for this batch.</Text>
      ) : (
        <Table horizontalSpacing="sm" verticalSpacing="xs">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>When</Table.Th>
              <Table.Th>Event</Table.Th>
              <Table.Th>Change</Table.Th>
              <Table.Th>Reference</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {movements.map((movement) => {
              const reference = getMovementReference(movement)
              const orderStatus = movement.sales_order?.status ?? movement.purchase_order?.status
              const orderPath = getOrderDetailPath(movement)

              return (
                <Table.Tr key={movement.id}>
                  <Table.Td>
                    <Text size="xs">{new Date(movement.created_at).toLocaleString()}</Text>
                  </Table.Td>
                  <Table.Td>
                    <Badge size="sm" variant="light" color="gray">
                      {getMovementLabel(movement.reason)}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Text size="xs" fw={600} c={getDeltaColor(movement.delta)}>
                      {formatSignedDelta(movement.delta, movement.product.unit_of_measure)}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <OrderReferenceCell
                      reference={reference}
                      orderPath={orderPath}
                      orderStatus={orderStatus}
                      textSize="xs"
                    />
                  </Table.Td>
                </Table.Tr>
              )
            })}
          </Table.Tbody>
        </Table>
      )}
    </Stack>
  )
}
