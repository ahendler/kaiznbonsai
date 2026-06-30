import { useState } from 'react'
import { Table, Badge, Button, Group, Text, ActionIcon, Loader, Center, Modal, Tooltip, Box } from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { IconCheck, IconX } from '@tabler/icons-react'
import { useDisclosure } from '@mantine/hooks'
import { usePurchaseOrders, useConfirmPurchaseOrder, useCancelPurchaseOrder } from '@/api/orders'
import type { PurchaseOrder } from '@/api/orders'
import { getApiErrorMessage } from '@/api/errors'
import { formatOrderMoney, orderStatusColor, sumLineTotals } from '@/utils/orders'
import { OrderActionConfirmModal } from '@/components/orders/OrderActionConfirmModal'
import { PurchaseOrderDrawer } from '@/components/orders/PurchaseOrderDrawer'

export function PurchaseOrderTable() {
  const { data: ordersData, isLoading, fetchNextPage, hasNextPage, isFetchingNextPage } = usePurchaseOrders()
  const confirmMutation = useConfirmPurchaseOrder()
  const cancelMutation = useCancelPurchaseOrder()
  const [opened, { open, close }] = useDisclosure(false)
  const [actionOrder, setActionOrder] = useState<{ id: number, action: 'confirm' | 'cancel' } | null>(null)
  const [viewOrder, setViewOrder] = useState<PurchaseOrder | null>(null)

  const orders = ordersData?.pages.flatMap(page => page.results) || []

  if (isLoading) return <Center p="xl"><Loader /></Center>

  const handleConfirm = (id: number) => {
    confirmMutation.mutate(id, {
      onSuccess: () => notifications.show({ title: 'Confirmed', message: 'Order confirmed. Stock has been generated!', color: 'green' }),
      onError: (err) => notifications.show({ title: 'Error', message: `Failed to confirm: ${getApiErrorMessage(err)}`, color: 'red' }),
    })
  }

  const handleCancel = (id: number) => {
    cancelMutation.mutate(id, {
      onSuccess: () => notifications.show({ title: 'Cancelled', message: 'Order cancelled.', color: 'blue' }),
      onError: (err) => notifications.show({ title: 'Cannot Cancel', message: getApiErrorMessage(err), color: 'red', autoClose: 6000 }),
    })
  }

  const rows = orders.map((order) => {
    const totalCost = sumLineTotals(order.items, 'unit_cost')

    return (
      <Table.Tr key={order.id} style={{ cursor: 'pointer' }} onClick={() => setViewOrder(order)}>
        <Table.Td>#{order.id}</Table.Td>
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
              <Tooltip label="Cancel Order (Reverts Stock)">
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
    ? 'This will generate stock batches for all items in this order.'
    : 'This will attempt to remove the generated stock batches. It cannot be undone if the stock has already been consumed.'

  return (
    <>
      <Group justify="space-between" mb="md">
        <Text size="lg" fw={500}>Inbound Shipments</Text>
        <Button onClick={open}>Create Purchase Order</Button>
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
        <Table.Tbody>{rows?.length ? rows : <Table.Tr><Table.Td colSpan={6}><Text c="dimmed" ta="center">No purchase orders found.</Text></Table.Td></Table.Tr>}</Table.Tbody>
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

      <Modal
        opened={!!viewOrder}
        onClose={() => setViewOrder(null)}
        title={
          <Group>
            <Text size="lg" fw={600}>Purchase Order #{viewOrder?.id}</Text>
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
              <Table.Th>Unit Cost</Table.Th>
              <Table.Th>Line Total</Table.Th>
              <Table.Th>Lot Code</Table.Th>
              <Table.Th>Best Before</Table.Th>
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
                <Table.Td>{formatOrderMoney(parseFloat(item.unit_cost))}</Table.Td>
                <Table.Td>{formatOrderMoney(parseFloat(item.quantity) * parseFloat(item.unit_cost))}</Table.Td>
                <Table.Td>{item.lot_code || '-'}</Table.Td>
                <Table.Td>{item.best_before || '-'}</Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
        <Group justify="space-between" mt="xl">
          <Text fw={600}>
            Total Price: {viewOrder ? formatOrderMoney(sumLineTotals(viewOrder.items, 'unit_cost')) : ''}
          </Text>
          <Button variant="default" onClick={() => setViewOrder(null)}>Close</Button>
        </Group>
      </Modal>
    </>
  )
}
