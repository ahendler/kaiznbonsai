import { useState } from 'react'
import { Table, Badge, Button, Group, Text, ActionIcon, Loader, Center, Modal, Tooltip, Box } from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { IconCheck, IconX } from '@tabler/icons-react'
import { useDisclosure } from '@mantine/hooks'
import { useSalesOrders, useConfirmSalesOrder, useCancelSalesOrder } from '@/api/orders'
import type { SalesOrder } from '@/api/orders'
import { getApiErrorMessage } from '@/api/errors'
import { formatOrderMoney, orderStatusColor, sumLineTotals } from '@/utils/orders'
import { OrderActionConfirmModal } from '@/components/orders/OrderActionConfirmModal'
import { SalesOrderDrawer } from '@/components/orders/SalesOrderDrawer'

export function SalesOrderTable() {
  const { data: ordersData, isLoading, fetchNextPage, hasNextPage, isFetchingNextPage } = useSalesOrders()
  const confirmMutation = useConfirmSalesOrder()
  const cancelMutation = useCancelSalesOrder()
  const [opened, { open, close }] = useDisclosure(false)
  const [actionOrder, setActionOrder] = useState<{ id: number, action: 'confirm' | 'cancel' } | null>(null)
  const [viewOrder, setViewOrder] = useState<SalesOrder | null>(null)

  const orders = ordersData?.pages.flatMap(page => page.results) || []

  if (isLoading) return <Center p="xl"><Loader /></Center>

  const handleConfirm = (id: number) => {
    confirmMutation.mutate(id, {
      onSuccess: () => notifications.show({ title: 'Confirmed', message: 'Sales order confirmed. Stock has been deducted!', color: 'green' }),
      onError: (err) => notifications.show({ title: 'Error', message: `Failed to confirm: ${getApiErrorMessage(err)}`, color: 'red' }),
    })
  }

  const handleCancel = (id: number) => {
    cancelMutation.mutate(id, {
      onSuccess: () => notifications.show({ title: 'Cancelled', message: 'Sales order cancelled.', color: 'blue' }),
      onError: (err) => notifications.show({ title: 'Cannot Cancel', message: getApiErrorMessage(err), color: 'red', autoClose: 6000 }),
    })
  }

  const rows = orders.map((order) => {
    const totalPrice = sumLineTotals(order.items, 'unit_price')

    return (
      <Table.Tr key={order.id} style={{ cursor: 'pointer' }} onClick={() => setViewOrder(order)}>
        <Table.Td>#{order.id}</Table.Td>
        <Table.Td>{new Date(order.created_at).toLocaleDateString()}</Table.Td>
        <Table.Td>
          <Badge color={orderStatusColor(order.status)}>{order.status}</Badge>
        </Table.Td>
        <Table.Td>{order.items.length} items</Table.Td>
        <Table.Td>{formatOrderMoney(totalPrice)}</Table.Td>
        <Table.Td>
          <Group gap="xs" wrap="nowrap" justify="center">
            {order.status === 'DRAFT' ? (
              <Tooltip label="Confirm Order (Deducts Stock via FIFO)">
                <ActionIcon variant="light" color="green" onClick={(e) => { e.stopPropagation(); setActionOrder({ id: order.id, action: 'confirm' }) }}>
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
              <Tooltip label="Cancel Order (Refunds Stock)">
                <ActionIcon variant="subtle" color="red" onClick={(e) => { e.stopPropagation(); setActionOrder({ id: order.id, action: 'cancel' }) }}>
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
    ? 'This will permanently deduct stock from your oldest available batches using FIFO.'
    : 'This will attempt to refund the deducted stock back to the inventory.'

  return (
    <>
      <Group justify="space-between" mb="md">
        <Text size="lg" fw={500}>Outbound Shipments</Text>
        <Button color="blue" onClick={open}>Create Sales Order</Button>
      </Group>

      <Table striped highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>ID</Table.Th>
            <Table.Th>Date</Table.Th>
            <Table.Th>Status</Table.Th>
            <Table.Th>Items</Table.Th>
            <Table.Th>Total Price</Table.Th>
            <Table.Th ta="center">Actions</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>{rows?.length ? rows : <Table.Tr><Table.Td colSpan={6}><Text c="dimmed" ta="center">No sales orders found.</Text></Table.Td></Table.Tr>}</Table.Tbody>
      </Table>

      {hasNextPage && (
        <Center mt="md">
          <Button variant="light" onClick={() => fetchNextPage()} loading={isFetchingNextPage}>
            Load More Orders
          </Button>
        </Center>
      )}

      <SalesOrderDrawer opened={opened} onClose={close} />

      <OrderActionConfirmModal
        opened={!!actionOrder}
        orderId={actionOrder?.id ?? null}
        action={actionOrder?.action ?? null}
        title={actionOrder?.action === 'confirm' ? 'Confirm Sales Order' : 'Cancel Sales Order'}
        description={actionDescription}
        loading={actionOrder?.action === 'confirm' ? confirmMutation.isPending : cancelMutation.isPending}
        onClose={() => setActionOrder(null)}
        onConfirm={(id) => {
          if (actionOrder?.action === 'confirm') handleConfirm(id)
          else handleCancel(id)
        }}
      />

      <Modal
        opened={!!viewOrder}
        onClose={() => setViewOrder(null)}
        title={
          <Group>
            <Text size="lg" fw={600}>Sales Order #{viewOrder?.id}</Text>
            {viewOrder?.title && <Badge variant="light">{viewOrder.title}</Badge>}
            {viewOrder && <Badge color={orderStatusColor(viewOrder.status)}>{viewOrder.status}</Badge>}
          </Group>
        }
        size="xl"
      >
        <Table striped mt="md">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Product</Table.Th>
              <Table.Th>Qty</Table.Th>
              <Table.Th>Unit Price</Table.Th>
              <Table.Th>Line Total</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {viewOrder?.items.map((item) => (
              <Table.Tr key={item.id}>
                <Table.Td>
                  <Text fw={500}>{item.product_details?.name}</Text>
                  <Text size="xs" c="dimmed">{item.product_details?.sku}</Text>
                </Table.Td>
                <Table.Td>{parseFloat(item.quantity)}</Table.Td>
                <Table.Td>{formatOrderMoney(parseFloat(item.unit_price))}</Table.Td>
                <Table.Td>{formatOrderMoney(parseFloat(item.quantity) * parseFloat(item.unit_price))}</Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
        <Group justify="space-between" mt="xl">
          <Text fw={600}>
            Total Price: {viewOrder ? formatOrderMoney(sumLineTotals(viewOrder.items, 'unit_price')) : ''}
          </Text>
          <Button variant="default" onClick={() => setViewOrder(null)}>Close</Button>
        </Group>
      </Modal>
    </>
  )
}
