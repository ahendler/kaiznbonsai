import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Anchor,
  Badge,
  Center,
  Group,
  Loader,
  Paper,
  SimpleGrid,
  Stack,
  Table,
  Text,
  ThemeIcon,
  Title,
  UnstyledButton,
} from '@mantine/core'
import {
  IconAlertTriangle,
  IconCash,
  IconChartBar,
  IconChevronRight,
  IconCircleCheck,
  IconHistory,
  IconPackage,
  IconTrendingDown,
  IconTrendingUp,
  IconTruckDelivery,
} from '@tabler/icons-react'
import { useQuery } from '@tanstack/react-query'
import FinancialPeriodFilter from '@/components/dashboard/FinancialPeriodFilter'
import OrderReferenceCell from '@/components/orders/OrderReferenceCell'
import { listStockMovements } from '@/api/activity'
import { useOverallFinancials, listProductFinancials } from '@/api/financials'
import { listProducts } from '@/api/inventory'
import { usePurchaseOrders, useSalesOrders } from '@/api/orders'
import { buildOrderPath } from '@/utils/orders'
import { formatCurrency, formatMarginPercent } from '@/utils/financials'
import {
  DEFAULT_FINANCIAL_PERIOD,
  formatFinancialPeriodLabel,
  isFinancialPeriodActive,
  isFinancialPeriodReady,
  toFinancialPeriodParams,
  type FinancialPeriod,
} from '@/utils/financialPeriod'
import {
  formatBatchLabel,
  formatSignedDelta,
  getDeltaColor,
  getMovementLabel,
  getMovementReference,
  getOrderDetailPath,
} from '@/utils/activity'

const RECENT_ACTIVITY_LIMIT = 10

type AttentionKind = 'negative_margin' | 'out_of_stock' | 'draft_purchase' | 'draft_sales'

interface AttentionItem {
  key: string
  kind: AttentionKind
  title: string
  description: string
  to: string
  color: string
  icon: typeof IconCash
  badge: string
}

const ATTENTION_KIND_META: Record<
  AttentionKind,
  { color: string; icon: typeof IconCash; badge: string }
> = {
  negative_margin: { color: 'red', icon: IconTrendingDown, badge: 'Loss maker' },
  out_of_stock: { color: 'orange', icon: IconPackage, badge: 'Stockout' },
  draft_purchase: { color: 'yellow', icon: IconTruckDelivery, badge: 'Purchase' },
  draft_sales: { color: 'blue', icon: IconCash, badge: 'Sales' },
}

export default function HomePage() {
  const [period, setPeriod] = useState<FinancialPeriod>(DEFAULT_FINANCIAL_PERIOD)

  const periodReady = isFinancialPeriodReady(period)
  const periodParams = periodReady ? toFinancialPeriodParams(period) : {}
  const periodActive = isFinancialPeriodActive(period)
  const periodLabel = formatFinancialPeriodLabel(period)
  const customPeriodIncomplete = period.preset === 'custom' && !periodReady

  const { data: overall, isLoading: overallLoading } = useOverallFinancials(periodParams, {
    enabled: periodReady,
  })

  const { data: negativeMarginProducts, isLoading: negativeLoading } = useQuery({
    queryKey: ['home', 'negative-margin', periodParams],
    queryFn: () => listProductFinancials(null, { ...periodParams, margin_band: 'negative' }),
    enabled: periodReady,
  })

  const { data: movementProducts, isLoading: movementLoading } = useQuery({
    queryKey: ['home', 'movement-products', periodParams],
    queryFn: () => listProductFinancials(null, { ...periodParams, activity: 'movement' }),
    enabled: periodReady,
  })

  const { data: outOfStockProducts, isLoading: oosLoading } = useQuery({
    queryKey: ['home', 'out-of-stock'],
    queryFn: () => listProducts(null, { in_stock: false }),
    enabled: periodReady,
  })

  const { data: purchaseOrders, isLoading: poLoading } = usePurchaseOrders()
  const { data: salesOrders, isLoading: soLoading } = useSalesOrders()

  const { data: recentMovements, isLoading: movementsLoading } = useQuery({
    queryKey: ['home', 'recent-movements', periodParams],
    queryFn: () => listStockMovements(null, periodParams),
    enabled: periodReady,
  })

  const outOfStockWithSales = useMemo(() => {
    if (!movementProducts || !outOfStockProducts) return []
    const oosIds = new Set(outOfStockProducts.results.map((p) => p.id))
    return movementProducts.results
      .filter((p) => oosIds.has(p.id) && Number(p.qty_sold) > 0)
      .slice(0, 5)
  }, [movementProducts, outOfStockProducts])

  const draftPurchaseOrders = useMemo(
    () =>
      purchaseOrders?.pages.flatMap((page) => page.results).filter((o) => o.status === 'DRAFT') ??
      [],
    [purchaseOrders],
  )

  const draftSalesOrders = useMemo(
    () =>
      salesOrders?.pages.flatMap((page) => page.results).filter((o) => o.status === 'DRAFT') ?? [],
    [salesOrders],
  )

  const attentionItems = useMemo((): AttentionItem[] => {
    const items: AttentionItem[] = []

    for (const product of negativeMarginProducts?.results.slice(0, 5) ?? []) {
      const meta = ATTENTION_KIND_META.negative_margin
      items.push({
        key: `loss-${product.id}`,
        kind: 'negative_margin',
        title: product.name,
        description: `${formatMarginPercent(product.margin)} gross margin this period`,
        to: '/financials',
        ...meta,
      })
    }

    for (const product of outOfStockWithSales) {
      const meta = ATTENTION_KIND_META.out_of_stock
      items.push({
        key: `oos-${product.id}`,
        kind: 'out_of_stock',
        title: product.name,
        description: `Out of stock — sold ${product.qty_sold} ${product.unit_of_measure} this period`,
        to: '/inventory/products?stock=out_of_stock',
        ...meta,
      })
    }

    if (draftPurchaseOrders.length > 0) {
      const count = draftPurchaseOrders.length
      const meta = ATTENTION_KIND_META.draft_purchase
      items.push({
        key: 'draft-po',
        kind: 'draft_purchase',
        title: `${count} draft purchase order${count === 1 ? '' : 's'}`,
        description: 'Waiting to be confirmed and received into stock',
        to: buildOrderPath('purchases'),
        ...meta,
      })
    }

    if (draftSalesOrders.length > 0) {
      const count = draftSalesOrders.length
      const meta = ATTENTION_KIND_META.draft_sales
      items.push({
        key: 'draft-so',
        kind: 'draft_sales',
        title: `${count} draft sales order${count === 1 ? '' : 's'}`,
        description: 'Waiting to be confirmed and fulfilled',
        to: buildOrderPath('sales'),
        ...meta,
      })
    }

    return items
  }, [
    negativeMarginProducts,
    outOfStockWithSales,
    draftPurchaseOrders.length,
    draftSalesOrders.length,
  ])

  const movements = recentMovements?.results.slice(0, RECENT_ACTIVITY_LIMIT) ?? []

  const summaryLoading = periodReady && overallLoading
  const attentionLoading =
    periodReady && (negativeLoading || movementLoading || oosLoading || poLoading || soLoading)

  if (summaryLoading && !overall) {
    return (
      <Center h="100%">
        <Loader />
      </Center>
    )
  }

  const stats = [
    { title: 'Total Revenue', value: formatCurrency(overall?.revenue || 0), icon: IconCash, color: 'blue' },
    { title: 'Gross Profit', value: formatCurrency(overall?.gross_profit || 0), icon: IconTrendingUp, color: 'green' },
    { title: 'COGS', value: formatCurrency(overall?.cogs || 0), icon: IconTrendingDown, color: 'red' },
    {
      title: 'Current Inventory Value',
      subtitle: periodActive ? 'Not filtered by period — stock on hand now' : undefined,
      value: formatCurrency(overall?.inventory_value || 0),
      icon: IconPackage,
      color: 'grape',
    },
  ]

  return (
    <Stack gap="xl">
      <Group justify="space-between" align="flex-start" wrap="wrap">
        <div>
          <Title order={2}>Home</Title>
          <Text c="dimmed" size="sm">
            Snapshot of your business for the selected period.
          </Text>
        </div>
        <Group gap="sm" wrap="wrap" align="center">
          <FinancialPeriodFilter value={period} onChange={setPeriod} />
          {periodLabel && period.preset !== 'custom' && (
            <Badge size="lg" variant="light" color="gray">
              {periodLabel}
            </Badge>
          )}
          <Anchor component={Link} to="/financials" size="sm">
            View financial details →
          </Anchor>
        </Group>
      </Group>

      {customPeriodIncomplete ? (
        <Paper shadow="sm" radius="md" p="xl" withBorder>
          <Center>
            <Stack align="center" gap="sm">
              <IconChartBar size={48} color="var(--mantine-color-gray-4)" />
              <Text c="dimmed" size="lg" fw={500}>
                Select a start and end date
              </Text>
              <Text c="dimmed" size="sm">
                Choose both dates in the custom range picker to load your snapshot.
              </Text>
            </Stack>
          </Center>
        </Paper>
      ) : (
        <Stack gap="xl">
          <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} spacing="lg">
            {stats.map((stat) => (
              <Paper key={stat.title} shadow="sm" p="lg" radius="md" withBorder>
                <Group justify="space-between" align="flex-start">
                  <div>
                    <Text size="sm" c="dimmed" fw={500} tt="uppercase">
                      {stat.title}
                    </Text>
                    {stat.subtitle && (
                      <Text size="xs" c="dimmed" mt={4}>
                        {stat.subtitle}
                      </Text>
                    )}
                  </div>
                  <ThemeIcon color={stat.color} variant="light" size="lg" radius="md">
                    <stat.icon size={20} stroke={1.5} />
                  </ThemeIcon>
                </Group>
                <Text size="xl" fw={700} mt="md">
                  {stat.value}
                </Text>
              </Paper>
            ))}
          </SimpleGrid>

          <Paper shadow="sm" radius="md" p="md" withBorder>
            <Group gap="xs" mb="md">
              <IconAlertTriangle size={18} stroke={1.5} />
              <Title order={4}>Needs attention</Title>
            </Group>

            {attentionLoading && attentionItems.length === 0 ? (
              <Center h={80}>
                <Loader size="sm" />
              </Center>
            ) : attentionItems.length === 0 ? (
              <Center py="lg">
                <Stack align="center" gap="xs">
                  <ThemeIcon color="green" variant="light" size="xl" radius="xl">
                    <IconCircleCheck size={22} stroke={1.5} />
                  </ThemeIcon>
                  <Text c="dimmed" size="sm" fw={500}>
                    Nothing flagged for this period
                  </Text>
                </Stack>
              </Center>
            ) : (
              <Stack gap="sm">
                {attentionItems.map((item) => {
                  const ItemIcon = item.icon
                  return (
                    <UnstyledButton
                      key={item.key}
                      component={Link}
                      to={item.to}
                      className="block w-full rounded-md transition-colors hover:bg-[var(--mantine-color-gray-0)]"
                    >
                      <Paper p="sm" radius="md" withBorder>
                        <Group wrap="nowrap" align="center" gap="sm">
                          <ThemeIcon color={item.color} variant="light" size="lg" radius="md">
                            <ItemIcon size={18} stroke={1.5} />
                          </ThemeIcon>
                          <Stack gap={2} style={{ flex: 1, minWidth: 0 }}>
                            <Group justify="space-between" wrap="nowrap" gap="xs">
                              <Text fw={600} size="sm" lineClamp={1}>
                                {item.title}
                              </Text>
                              <Badge size="xs" variant="light" color={item.color}>
                                {item.badge}
                              </Badge>
                            </Group>
                            <Text size="xs" c="dimmed" lineClamp={2}>
                              {item.description}
                            </Text>
                          </Stack>
                          <IconChevronRight
                            size={16}
                            stroke={1.5}
                            color="var(--mantine-color-gray-5)"
                            style={{ flexShrink: 0 }}
                          />
                        </Group>
                      </Paper>
                    </UnstyledButton>
                  )
                })}
              </Stack>
            )}
          </Paper>

          <Paper shadow="sm" radius="md" p="md" withBorder>
            <Group justify="space-between" mb="md">
              <Group gap="xs">
                <IconHistory size={18} stroke={1.5} />
                <Title order={4}>Recent activity</Title>
              </Group>
              <Anchor component={Link} to="/history" size="sm">
                View all →
              </Anchor>
            </Group>

            {movementsLoading ? (
              <Center h={120}>
                <Loader size="sm" />
              </Center>
            ) : movements.length === 0 ? (
              <Text c="dimmed" size="sm">
                No stock movements in this period.
              </Text>
            ) : (
              <Table striped highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>When</Table.Th>
                    <Table.Th>Event</Table.Th>
                    <Table.Th>Product</Table.Th>
                    <Table.Th>Change</Table.Th>
                    <Table.Th>Reference</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {movements.map((movement) => {
                    const reference = getMovementReference(movement)
                    const orderStatus =
                      movement.sales_order?.status ?? movement.purchase_order?.status

                    return (
                      <Table.Tr key={movement.id}>
                        <Table.Td>
                          <Text size="sm">
                            {new Date(movement.created_at).toLocaleString()}
                          </Text>
                        </Table.Td>
                        <Table.Td>
                          <Badge variant="light" color="gray">
                            {getMovementLabel(movement.reason)}
                          </Badge>
                        </Table.Td>
                        <Table.Td>
                          <Text size="sm" fw={500}>
                            {movement.product.name}
                          </Text>
                          <Text size="xs" c="dimmed">
                            {formatBatchLabel(
                              movement.stock_batch.lot_code,
                              movement.stock_batch.id,
                            )}
                          </Text>
                        </Table.Td>
                        <Table.Td>
                          <Text size="sm" fw={600} c={getDeltaColor(movement.delta)}>
                            {formatSignedDelta(movement.delta, movement.product.unit_of_measure)}
                          </Text>
                        </Table.Td>
                        <Table.Td>
                          <OrderReferenceCell
                            reference={reference}
                            orderPath={getOrderDetailPath(movement)}
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
          </Paper>
        </Stack>
      )}
    </Stack>
  )
}
