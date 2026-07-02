import { useState } from 'react'
import { Table, Badge, Button, Group, Text, ActionIcon, Loader, Center, Tooltip, Box } from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { IconCheck, IconX } from '@tabler/icons-react'
import { useDisclosure } from '@mantine/hooks'
import { usePurchaseOrders, useConfirmPurchaseOrder, useCancelPurchaseOrder } from '@/api/orders'
import type { OrderListFilters, PurchaseOrder } from '@/api/orders'
import { getApiErrorMessage } from '@/api/errors'
import { formatOrderMoney, getPurchaseOrderCancelDescription, getPurchaseOrderCancelTooltip, orderStatusColor, sumLineTotals, type OrderStatusFilter } from '@/utils/orders'
import { OrderActionConfirmModal } from '@/components/orders/OrderActionConfirmModal'
import { OrderStatusFilterSelect } from '@/components/orders/OrderStatusFilterSelect'
import { OrderTableTitleCell, ORDER_NAME_COLUMN_MAX_WIDTH } from '@/components/orders/OrderTableTitleCell'
import { PurchaseOrderDrawer } from '@/components/orders/PurchaseOrderDrawer'

interface PurchaseOrderTableProps {
  listFilters: OrderListFilters
  statusFilter: OrderStatusFilter
  onStatusFilterChange: (value: OrderStatusFilter) => void
  onViewOrder?: (order: PurchaseOrder) => void
}

export function PurchaseOrderTable({
  listFilters,
  statusFilter,
  onStatusFilterChange,
  onViewOrder,
}: PurchaseOrderTableProps) {
  const { data: ordersData, isLoading, fetchNextPage, hasNextPage, isFetchingNextPage } = usePurchaseOrders(listFilters)
  const confirmMutation = useConfirmPurchaseOrder()
  const cancelMutation = useCancelPurchaseOrder()
  const [opened, { open, close }] = useDisclosure(false)
  const [actionOrder, setActionOrder] = useState<{
    id: number
    action: 'confirm' | 'cancel'
    status: PurchaseOrder['status']
  } | null>(null)

  const orders = ordersData?.pages.flatMap(page => page.results) || []
  const hasStatusFilter = statusFilter !== 'all'

  if (isLoading) return <Center p="xl"><Loader /></Center>

  const handleConfirm = (id: number) => {
    confirmMutation.mutate(id, {
      onSuccess: () => {
        setActionOrder(null)
        notifications.show({ title: 'Confirmed', message: 'Order confirmed. Stock has been generated!', color: 'green' })
      },
      onError: (err) => notifications.show({ title: 'Error', message: `Failed to confirm: ${getApiErrorMessage(err)}`, color: 'red' }),
    })
  }

  const handleCancel = (id: number) => {
    cancelMutation.mutate(id, {
      onSuccess: () => {
        setActionOrder(null)
        notifications.show({ title: 'Cancelled', message: 'Order cancelled.', color: 'blue' })
      },
      onError: (err) => notifications.show({ title: 'Cannot Cancel', message: getApiErrorMessage(err), color: 'red', autoClose: 6000 }),
    })
  }

  const rows = orders.map((order) => {
    const totalCost = sumLineTotals(order.items, 'unit_cost')

    return (
      <Table.Tr key={order.id} style={{ cursor: onViewOrder ? 'pointer' : undefined }} onClick={() => onViewOrder?.(order)}>
        <Table.Td>#{order.id}</Table.Td>
        <Table.Td maw={ORDER_NAME_COLUMN_MAX_WIDTH}>
          <OrderTableTitleCell title={order.title} />
        </Table.Td>
        <Table.Td>{new Date(order.created_at).toLocaleDateString()}</Table.Td>
        <Table.Td>
          <Badge color={orderStatusColor(order.status)}>{order.status}</Badge>
        </Table.Td>
        <Table.Td>{order.items.length} items</Table.Td>
        <Table.Td>{formatOrderMoney(totalCost)}</Table.Td>
        <Table.Td>
          <Group gap="xs" wrap="nowrap" justify="center">
            {order.status === 'DRAFT' ? (
              <Tooltip label="Confirm Order (Generates Stock)">
                <ActionIcon variant="light" color="green" onClick={(e) => { e.stopPropagation(); setActionOrder({ id: order.id, action: 'confirm', status: order.status }) }}>
                  <IconCheck size={16} />
                </ActionIcon>
              </Tooltip>
            ) : (
              <Tooltip label="Order already confirmed">
                <Box display="inline-block">
                  <ActionIcon variant="subtle" color="gray" disabled style={{ pointerEvents: 'none' }}>
                    <IconCheck size={16} />
                  </ActionIcon>
                </Box>
              </Tooltip>
            )}

            {order.status !== 'CANCELLED' ? (
              <Tooltip label={getPurchaseOrderCancelTooltip(order.status)}>
                <ActionIcon variant="subtle" color="red" onClick={(e) => { e.stopPropagation(); setActionOrder({ id: order.id, action: 'cancel', status: order.status }) }}>
                  <IconX size={16} />
                </ActionIcon>
              </Tooltip>
            ) : (
              <Tooltip label="Order already cancelled">
                <Box display="inline-block">
                  <ActionIcon variant="subtle" color="gray" disabled style={{ pointerEvents: 'none' }}>
                    <IconX size={16} />
                  </ActionIcon>
                </Box>
              </Tooltip>
            )}
          </Group>
        </Table.Td>
      </Table.Tr>
    )
  })

  const actionDescription = actionOrder?.action === 'confirm'
    ? 'This will generate stock batches for all items in this order.'
    : actionOrder
      ? getPurchaseOrderCancelDescription(actionOrder.status)
      : ''

  return (
    <>
      <Group justify="space-between" mb="md" wrap="wrap">
        <Group gap="md" wrap="wrap">
          <Text size="lg" fw={500}>Inbound Shipments</Text>
          <OrderStatusFilterSelect value={statusFilter} onChange={onStatusFilterChange} />
        </Group>
        <Button onClick={open}>Create Purchase Order</Button>
      </Group>

      <Table striped highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>ID</Table.Th>
            <Table.Th maw={ORDER_NAME_COLUMN_MAX_WIDTH}>Name</Table.Th>
            <Table.Th>Date</Table.Th>
            <Table.Th>Status</Table.Th>
            <Table.Th>Items</Table.Th>
            <Table.Th>Total Price</Table.Th>
            <Table.Th ta="center">Actions</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {rows?.length ? (
            rows
          ) : (
            <Table.Tr>
              <Table.Td colSpan={7}>
                <Text c="dimmed" ta="center">
                  {hasStatusFilter
                    ? 'No purchase orders match your status filter.'
                    : 'No purchase orders found.'}
                </Text>
              </Table.Td>
            </Table.Tr>
          )}
        </Table.Tbody>
      </Table>

      {hasNextPage && (
        <Center mt="md">
          <Button variant="light" onClick={() => fetchNextPage()} loading={isFetchingNextPage}>
            Load More Orders
          </Button>
        </Center>
      )}

      <PurchaseOrderDrawer opened={opened} onClose={close} />

      <OrderActionConfirmModal
        opened={!!actionOrder}
        orderId={actionOrder?.id ?? null}
        action={actionOrder?.action ?? null}
        title={actionOrder?.action === 'confirm' ? 'Confirm Purchase Order' : 'Cancel Purchase Order'}
        description={actionDescription}
        loading={actionOrder?.action === 'confirm' ? confirmMutation.isPending : cancelMutation.isPending}
        onClose={() => setActionOrder(null)}
        onConfirm={(id) => {
          if (actionOrder?.action === 'confirm') handleConfirm(id)
          else handleCancel(id)
        }}
      />
    </>
  )
}
