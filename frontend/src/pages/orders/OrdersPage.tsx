import { Container, Title, Tabs } from '@mantine/core'
import { IconTruckDelivery, IconCash } from '@tabler/icons-react'
import { useSearchParams } from 'react-router-dom'
import { PurchaseOrderTable } from '@/components/orders/PurchaseOrderTable'
import { SalesOrderTable } from '@/components/orders/SalesOrderTable'
import OrderDetailModal from '@/components/orders/OrderDetailModal'
import { usePurchaseOrder, useSalesOrder } from '@/api/orders'

export type OrdersTab = 'purchases' | 'sales'

function parseOrdersTab(value: string | null): OrdersTab {
  return value === 'sales' ? 'sales' : 'purchases'
}

function parseOrderId(value: string | null): number | null {
  if (!value) return null
  const id = Number.parseInt(value, 10)
  if (!Number.isFinite(id) || id <= 0) return null
  return id
}

export default function OrdersPage() {
  const [searchParams, setSearchParams] = useSearchParams()

  const tab = parseOrdersTab(searchParams.get('tab'))
  const orderId = parseOrderId(searchParams.get('orderId'))

  const salesOrderId = tab === 'sales' ? orderId : null
  const purchaseOrderId = tab === 'purchases' ? orderId : null

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
    const next = new URLSearchParams()
    if (tab !== 'purchases') {
      next.set('tab', tab)
    }
    setSearchParams(next, { replace: true })
  }

  const openSalesOrder = (id: number) => {
    setSearchParams({ tab: 'sales', orderId: String(id) }, { replace: true })
  }

  const openPurchaseOrder = (id: number) => {
    setSearchParams({ tab: 'purchases', orderId: String(id) }, { replace: true })
  }

  const handleTabChange = (value: string | null) => {
    if (!value) return
    setSearchParams({ tab: value }, { replace: true })
  }

  return (
    <Container size="xl">
      <Title order={2} mb="xl">
        Orders
      </Title>

      <Tabs value={tab} onChange={handleTabChange}>
        <Tabs.List mb="md">
          <Tabs.Tab value="purchases" leftSection={<IconTruckDelivery size={16} />}>
            Purchase Orders
          </Tabs.Tab>
          <Tabs.Tab value="sales" leftSection={<IconCash size={16} />}>
            Sales Orders
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="purchases" pt="md">
          <PurchaseOrderTable onViewOrder={(order) => openPurchaseOrder(order.id)} />
        </Tabs.Panel>

        <Tabs.Panel value="sales" pt="md">
          <SalesOrderTable onViewOrder={(order) => openSalesOrder(order.id)} />
        </Tabs.Panel>
      </Tabs>

      <OrderDetailModal
        variant="sales"
        opened={salesOrderId !== null}
        order={salesOrder}
        loading={salesOrderLoading}
        error={salesOrderError}
        onClose={closeOrderModal}
      />

      <OrderDetailModal
        variant="purchase"
        opened={purchaseOrderId !== null}
        order={purchaseOrder}
        loading={purchaseOrderLoading}
        error={purchaseOrderError}
        onClose={closeOrderModal}
      />
    </Container>
  )
}
