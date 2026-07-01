import { Badge, Button, Center, Group, Loader, Modal, Table, Text } from '@mantine/core'
import type { PurchaseOrder, SalesOrder } from '@/api/orders'
import { formatOrderMoney, orderStatusColor, sumLineTotals } from '@/utils/orders'

type SalesOrderDetailModalProps = {
  variant: 'sales'
  order: SalesOrder | null | undefined
  opened: boolean
  loading?: boolean
  error?: boolean
  onClose: () => void
}

type PurchaseOrderDetailModalProps = {
  variant: 'purchase'
  order: PurchaseOrder | null | undefined
  opened: boolean
  loading?: boolean
  error?: boolean
  onClose: () => void
}

export type OrderDetailModalProps = SalesOrderDetailModalProps | PurchaseOrderDetailModalProps

function OrderDetailTitle({
  variant,
  order,
}: {
  variant: 'sales' | 'purchase'
  order: SalesOrder | PurchaseOrder
}) {
  const label = variant === 'sales' ? 'Sales Order' : 'Purchase Order'

  return (
    <Group>
      <Text size="lg" fw={600}>{label} #{order.id}</Text>
      {order.title && <Badge variant="light">{order.title}</Badge>}
      <Badge color={orderStatusColor(order.status)}>{order.status}</Badge>
    </Group>
  )
}

export default function OrderDetailModal(props: OrderDetailModalProps) {
  const { opened, onClose, loading, error } = props
  const order = props.order ?? null

  const totalAmount = order
    ? props.variant === 'sales'
      ? formatOrderMoney(sumLineTotals(order.items, 'unit_price'))
      : formatOrderMoney(sumLineTotals(order.items, 'unit_cost'))
    : ''

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={order ? <OrderDetailTitle variant={props.variant} order={order} /> : 'Order details'}
      size="xl"
    >
      {loading && (
        <Center py="xl">
          <Loader />
        </Center>
      )}

      {error && !loading && (
        <Text c="red" py="md">Could not load this order.</Text>
      )}

      {!loading && !error && order && props.variant === 'sales' && (
        <>
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
              {order.items.map((item) => (
                <Table.Tr key={item.id}>
                  <Table.Td>
                    <Text fw={500}>{item.product_details?.name}</Text>
                    <Text size="xs" c="dimmed">{item.product_details?.sku}</Text>
                  </Table.Td>
                  <Table.Td>{parseFloat(item.quantity)}</Table.Td>
                  <Table.Td>{formatOrderMoney(parseFloat(item.unit_price))}</Table.Td>
                  <Table.Td>
                    {formatOrderMoney(parseFloat(item.quantity) * parseFloat(item.unit_price))}
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
          <Group justify="space-between" mt="xl">
            <Text fw={600}>Total Price: {totalAmount}</Text>
            <Button variant="default" onClick={onClose}>Close</Button>
          </Group>
        </>
      )}

      {!loading && !error && order && props.variant === 'purchase' && (
        <>
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
              {order.items.map((item) => (
                <Table.Tr key={item.id}>
                  <Table.Td>
                    <Text fw={500}>{item.product_details?.name}</Text>
                    <Text size="xs" c="dimmed">{item.product_details?.sku}</Text>
                  </Table.Td>
                  <Table.Td>{parseFloat(item.quantity)}</Table.Td>
                  <Table.Td>{formatOrderMoney(parseFloat(item.unit_cost))}</Table.Td>
                  <Table.Td>
                    {formatOrderMoney(parseFloat(item.quantity) * parseFloat(item.unit_cost))}
                  </Table.Td>
                  <Table.Td>{item.lot_code || '-'}</Table.Td>
                  <Table.Td>{item.best_before || '-'}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
          <Group justify="space-between" mt="xl">
            <Text fw={600}>Total Price: {totalAmount}</Text>
            <Button variant="default" onClick={onClose}>Close</Button>
          </Group>
        </>
      )}
    </Modal>
  )
}
