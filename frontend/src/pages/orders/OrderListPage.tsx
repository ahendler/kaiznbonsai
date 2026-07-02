import { useMemo } from 'react'
import { Container, Title } from '@mantine/core'
import { useSearchParams } from 'react-router-dom'
import { PurchaseOrderTable } from '@/components/orders/PurchaseOrderTable'
import { SalesOrderTable } from '@/components/orders/SalesOrderTable'
import OrderDetailModal from '@/components/orders/OrderDetailModal'
import { usePurchaseOrder, useSalesOrder } from '@/api/orders'
import type { OrderListFilters } from '@/api/orders'
import {
  orderStatusSlugToApi,
  parseOrderId,
  parseOrderStatusFilter,
  type OrderKind,
  type OrderStatusFilter,
} from '@/utils/orders'

interface Props {
  kind: OrderKind
  title: string
}

export default function OrderListPage({ kind, title }: Props) {
  const [searchParams, setSearchParams] = useSearchParams()
  const orderId = parseOrderId(searchParams.get('orderId'))
  const statusFilter = parseOrderStatusFilter(searchParams.get('status'))

  const listFilters = useMemo((): OrderListFilters => {
    if (statusFilter === 'all') return {}
    return { status: orderStatusSlugToApi(statusFilter) }
  }, [statusFilter])

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

  const setStatusFilter = (filter: OrderStatusFilter) => {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        if (filter === 'all') {
          next.delete('status')
        } else {
          next.set('status', filter)
        }
        return next
      },
      { replace: true },
    )
  }

  const closeOrderModal = () => {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        next.delete('orderId')
        return next
      },
      { replace: true },
    )
  }

  const openOrder = (id: number) => {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        next.set('orderId', String(id))
        return next
      },
      { replace: true },
    )
  }

  return (
    <Container size="xl">
      <Title order={2} mb="xl">
        {title}
      </Title>

      {kind === 'purchases' ? (
        <PurchaseOrderTable
          listFilters={listFilters}
          statusFilter={statusFilter}
          onStatusFilterChange={setStatusFilter}
          onViewOrder={(order) => openOrder(order.id)}
        />
      ) : (
        <SalesOrderTable
          listFilters={listFilters}
          statusFilter={statusFilter}
          onStatusFilterChange={setStatusFilter}
          onViewOrder={(order) => openOrder(order.id)}
        />
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
