import { useMemo } from 'react'
import { Button, Container, Group } from '@mantine/core'
import { useDisclosure } from '@mantine/hooks'
import { useSearchParams } from 'react-router-dom'
import { PurchaseOrderTable } from '@/components/orders/PurchaseOrderTable'
import { SalesOrderTable } from '@/components/orders/SalesOrderTable'
import OrderDetailModal from '@/components/orders/OrderDetailModal'
import { OrderStatusFilterSelect } from '@/components/orders/OrderStatusFilterSelect'
import { PurchaseOrderDrawer } from '@/components/orders/PurchaseOrderDrawer'
import { SalesOrderDrawer } from '@/components/orders/SalesOrderDrawer'
import { PageTitle } from '@/components/layout/PageTitle'
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
  subtitle: string
}

export default function OrderListPage({ kind, title, subtitle }: Props) {
  const [searchParams, setSearchParams] = useSearchParams()
  const [createOpened, { open: openCreate, close: closeCreate }] = useDisclosure(false)
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
      <Group justify="space-between" align="baseline" mb="xl" wrap="wrap" gap="md">
        <PageTitle title={title} subtitle={subtitle} />
        <Group gap="md" wrap="wrap">
          <OrderStatusFilterSelect value={statusFilter} onChange={setStatusFilter} />
          {kind === 'purchases' ? (
            <Button onClick={openCreate}>Create Purchase Order</Button>
          ) : (
            <Button color="blue" onClick={openCreate}>
              Create Sales Order
            </Button>
          )}
        </Group>
      </Group>

      {kind === 'purchases' ? (
        <PurchaseOrderTable
          listFilters={listFilters}
          statusFilter={statusFilter}
          onViewOrder={(order) => openOrder(order.id)}
        />
      ) : (
        <SalesOrderTable
          listFilters={listFilters}
          statusFilter={statusFilter}
          onViewOrder={(order) => openOrder(order.id)}
        />
      )}

      {kind === 'sales' && (
        <>
          <SalesOrderDrawer opened={createOpened} onClose={closeCreate} />
          <OrderDetailModal
            variant="sales"
            opened={salesOrderId !== null}
            order={salesOrder}
            loading={salesOrderLoading}
            error={salesOrderError}
            onClose={closeOrderModal}
          />
        </>
      )}

      {kind === 'purchases' && (
        <>
          <PurchaseOrderDrawer opened={createOpened} onClose={closeCreate} />
          <OrderDetailModal
            variant="purchase"
            opened={purchaseOrderId !== null}
            order={purchaseOrder}
            loading={purchaseOrderLoading}
            error={purchaseOrderError}
            onClose={closeOrderModal}
          />
        </>
      )}
    </Container>
  )
}
