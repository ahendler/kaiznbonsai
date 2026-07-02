import { useState } from 'react'
import { Table, Badge, Button, Group, Text, ActionIcon, Loader, Center, Tooltip, Box } from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { IconCheck, IconX } from '@tabler/icons-react'
import { useSalesOrders, useConfirmSalesOrder, useCancelSalesOrder } from '@/api/orders'
import type { OrderListFilters, SalesOrder, StockAllocationStrategy } from '@/api/orders'
import { getApiErrorMessage } from '@/api/errors'
import { DEFAULT_ALLOCATION_STRATEGY, formatOrderMoney, getSalesOrderCancelDescription, getSalesOrderCancelTooltip, orderStatusColor, sumLineTotals, type OrderStatusFilter } from '@/utils/orders'
import { OrderActionConfirmModal } from '@/components/orders/OrderActionConfirmModal'
import { OrderTableTitleCell, ORDER_NAME_COLUMN_MAX_WIDTH } from '@/components/orders/OrderTableTitleCell'

interface SalesOrderTableProps {
  listFilters: OrderListFilters
  statusFilter: OrderStatusFilter
  onViewOrder?: (order: SalesOrder) => void
}

export function SalesOrderTable({
  listFilters,
  statusFilter,
  onViewOrder,
}: SalesOrderTableProps) {
  const { data: ordersData, isLoading, fetchNextPage, hasNextPage, isFetchingNextPage } = useSalesOrders(listFilters)
  const confirmMutation = useConfirmSalesOrder()
  const cancelMutation = useCancelSalesOrder()
  const [actionOrder, setActionOrder] = useState<{
    id: number
    action: 'confirm' | 'cancel'
    status: SalesOrder['status']
  } | null>(null)
  const [allocationStrategy, setAllocationStrategy] = useState<StockAllocationStrategy>(DEFAULT_ALLOCATION_STRATEGY)

  const orders = ordersData?.pages.flatMap(page => page.results) || []
  const hasStatusFilter = statusFilter !== 'all'

  if (isLoading) return <Center p="xl"><Loader /></Center>

  const handleConfirm = (id: number) => {
    confirmMutation.mutate(
      { id, allocationStrategy },
      {
        onSuccess: () => {
          setActionOrder(null)
          notifications.show({
            title: 'Confirmed',
            message: 'Sales order confirmed. Stock has been deducted.',
            color: 'green',
          })
        },
        onError: (err) => notifications.show({
          title: 'Error',
          message: `Failed to confirm: ${getApiErrorMessage(err)}`,
          color: 'red',
        }),
      },
    )
  }

  const handleCancel = (id: number) => {
    cancelMutation.mutate(id, {
      onSuccess: () => {
        setActionOrder(null)
        notifications.show({ title: 'Cancelled', message: 'Sales order cancelled.', color: 'blue' })
      },
      onError: (err) => notifications.show({ title: 'Cannot Cancel', message: getApiErrorMessage(err), color: 'red', autoClose: 6000 }),
    })
  }

  const openConfirmModal = (orderId: number, status: SalesOrder['status']) => {
    setAllocationStrategy(DEFAULT_ALLOCATION_STRATEGY)
    setActionOrder({ id: orderId, action: 'confirm', status })
  }

  const rows = orders.map((order) => {
    const totalPrice = sumLineTotals(order.items, 'unit_price')

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
        <Table.Td>{formatOrderMoney(totalPrice)}</Table.Td>
        <Table.Td>
          <Group gap="xs" wrap="nowrap" justify="center">
            {order.status === 'DRAFT' ? (
              <Tooltip label="Confirm order">
                <ActionIcon variant="light" color="green" onClick={(e) => { e.stopPropagation(); openConfirmModal(order.id, order.status) }}>
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
              <Tooltip label={getSalesOrderCancelTooltip(order.status)}>
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
    ? 'This will permanently deduct stock from your inventory.'
    : actionOrder
      ? getSalesOrderCancelDescription(actionOrder.status)
      : ''

  return (
    <>
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
                    ? 'No sales orders match your status filter.'
                    : 'No sales orders found.'}
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

      <OrderActionConfirmModal
        opened={!!actionOrder}
        orderId={actionOrder?.id ?? null}
        action={actionOrder?.action ?? null}
        title={actionOrder?.action === 'confirm' ? 'Confirm Sales Order' : 'Cancel Sales Order'}
        description={actionDescription}
        loading={actionOrder?.action === 'confirm' ? confirmMutation.isPending : cancelMutation.isPending}
        showAllocationToggle={actionOrder?.action === 'confirm'}
        allocationStrategy={allocationStrategy}
        onAllocationStrategyChange={setAllocationStrategy}
        onClose={() => setActionOrder(null)}
        onConfirm={(id) => {
          if (actionOrder?.action === 'confirm') handleConfirm(id)
          else handleCancel(id)
        }}
      />
    </>
  )
}
