import { Container, Title } from '@mantine/core'
import { useSearchParams } from 'react-router-dom'
import { PurchaseOrderTable } from '@/components/orders/PurchaseOrderTable'
import { SalesOrderTable } from '@/components/orders/SalesOrderTable'
import OrderDetailModal from '@/components/orders/OrderDetailModal'
import { usePurchaseOrder, useSalesOrder } from '@/api/orders'
import { parseOrderId, type OrderKind } from '@/utils/orders'

interface Props {
  kind: OrderKind
  title: string
}

export default function OrderListPage({ kind, title }: Props) {
  const [searchParams, setSearchParams] = useSearchParams()
  const orderId = parseOrderId(searchParams.get('orderId'))

  const salesOrderId = kind === 'sales' ? orderId : null
  const purchaseOrderId = kind === 'purchases' ? orderId : null

  const {
    data: salesOrder,
    isLoading: salesOrderLoading,
    isError: salesOrderError,
  } = useSalesOrder(salesOrderId)

  const {
    data: purchaseOrder,
    isLoading: purchaseOrderLoading,
    isError: purchaseOrderError,
  } = usePurchaseOrder(purchaseOrderId)

  const closeOrderModal = () => {
    setSearchParams({}, { replace: true })
  }

  const openOrder = (id: number) => {
    setSearchParams({ orderId: String(id) }, { replace: true })
  }

  return (
    <Container size="xl">
      <Title order={2} mb="xl">
        {title}
      </Title>

      {kind === 'purchases' ? (
        <PurchaseOrderTable onViewOrder={(order) => openOrder(order.id)} />
      ) : (
        <SalesOrderTable onViewOrder={(order) => openOrder(order.id)} />
      )}

      {kind === 'sales' && (
        <OrderDetailModal
          variant="sales"
          opened={salesOrderId !== null}
          order={salesOrder}
          loading={salesOrderLoading}
          error={salesOrderError}
          onClose={closeOrderModal}
        />
      )}

      {kind === 'purchases' && (
        <OrderDetailModal
          variant="purchase"
          opened={purchaseOrderId !== null}
          order={purchaseOrder}
          loading={purchaseOrderLoading}
          error={purchaseOrderError}
          onClose={closeOrderModal}
        />
      )}
    </Container>
  )
}
