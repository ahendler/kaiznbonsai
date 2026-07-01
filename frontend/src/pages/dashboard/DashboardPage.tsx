import { useEffect, useState } from 'react'
import {
  SimpleGrid, Card, Text, Group, Center, Loader,
  Table, Progress, Badge, Title, ThemeIcon, Stack, Paper,
} from '@mantine/core'
import {
  IconCash, IconTrendingUp, IconTrendingDown, IconPackage, IconChartBar,
} from '@tabler/icons-react'
import { useDebouncedValue, useIntersection } from '@mantine/hooks'
import { notifications } from '@mantine/notifications'
import DashboardProductFilters from '@/components/dashboard/DashboardProductFilters'
import {
  useOverallFinancials,
  useInfiniteProductFinancials,
  type ActivityFilter,
  type MarginBand,
  type ProductFinancialListFilters,
} from '@/api/financials'
import { getApiErrorMessage } from '@/api/errors'
import FinancialPeriodFilter from '@/components/dashboard/FinancialPeriodFilter'
import { formatCurrency, formatMarginPercent, formatQuantity, getMarginColor } from '@/utils/financials'
import {
  DEFAULT_FINANCIAL_PERIOD,
  formatFinancialPeriodLabel,
  isFinancialPeriodActive,
  toFinancialPeriodParams,
  type FinancialPeriod,
} from '@/utils/financialPeriod'

export default function DashboardPage() {
  const [period, setPeriod] = useState<FinancialPeriod>(DEFAULT_FINANCIAL_PERIOD)
  const [search, setSearch] = useState('')
  const [marginBand, setMarginBand] = useState<MarginBand | null>(null)
  const [activityFilter, setActivityFilter] = useState<ActivityFilter>('all')
  const [debouncedSearch] = useDebouncedValue(search, 300)

  const periodParams = toFinancialPeriodParams(period)
  const periodActive = isFinancialPeriodActive(period)
  const periodLabel = formatFinancialPeriodLabel(period)

  const tableFilters: ProductFinancialListFilters = {
    ...periodParams,
    search: debouncedSearch,
    ...(marginBand ? { margin_band: marginBand } : {}),
    ...(activityFilter !== 'all' ? { activity: activityFilter } : {}),
  }

  const hasActiveTableFilters = Boolean(
    debouncedSearch || marginBand || activityFilter !== 'all',
  )

  const {
    data: overall,
    isLoading: overallLoading,
    isError: overallError,
    error: overallErrorObj,
  } = useOverallFinancials(periodParams)

  const {
    data: productPages,
    isLoading: productsLoading,
    isFetching: productsFetching,
    isFetchingNextPage,
    fetchNextPage,
    hasNextPage,
    isError: productsError,
    error: productsErrorObj,
  } = useInfiniteProductFinancials(tableFilters)

  const products = productPages?.pages.flatMap((page) => page.results) ?? []

  const { ref, entry } = useIntersection({ threshold: 1 })

  useEffect(() => {
    if (entry?.isIntersecting && hasNextPage && !isFetchingNextPage) {
      fetchNextPage()
    }
  }, [entry?.isIntersecting, hasNextPage, isFetchingNextPage, fetchNextPage])

  useEffect(() => {
    const err = overallError ? overallErrorObj : productsError ? productsErrorObj : null
    if (err) {
      notifications.show({
        title: 'Could not load financials',
        message: getApiErrorMessage(err, 'Invalid period or server error.'),
        color: 'red',
      })
    }
  }, [overallError, overallErrorObj, productsError, productsErrorObj])

  const initialLoading = (overallLoading || productsLoading) && !overall && !productPages
  const isTableRefreshing = productsFetching && !isFetchingNextPage

  if (initialLoading) {
    return <Center h="100%"><Loader /></Center>
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
      <Group justify="space-between" align="center" wrap="wrap">
        <div>
          <Title order={2}>Financial Overview</Title>
          <Text c="dimmed" size="sm">High-level metrics and product performance.</Text>
        </div>
        <Group gap="sm" wrap="wrap" align="center">
          <FinancialPeriodFilter value={period} onChange={setPeriod} />
          {periodLabel && period.preset !== 'custom' && (
            <Badge size="lg" variant="light" color="gray">
              {periodLabel}
            </Badge>
          )}
          <Badge size="xl" variant="light" color="blue">
            Overall Margin: {formatMarginPercent(overall?.margin || 0)}
          </Badge>
        </Group>
      </Group>

      <Stack gap="xl">
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} spacing="lg">
          {stats.map((stat) => (
            <Card key={stat.title} shadow="sm" padding="lg" radius="md" withBorder>
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
              <Group align="flex-end" gap="xs" mt={25}>
                <Text size="xl" fw={700}>
                  {stat.value}
                </Text>
              </Group>
            </Card>
          ))}
        </SimpleGrid>

        <Paper shadow="sm" radius="md" p="md" withBorder pos="relative">
          {isTableRefreshing && (
            <Center
              pos="absolute"
              inset={0}
              style={{ zIndex: 1, backgroundColor: 'rgba(255, 255, 255, 0.6)' }}
            >
              <Loader size="sm" />
            </Center>
          )}

          <Title order={4} mb="md">Product Performance</Title>
            <DashboardProductFilters
              search={search}
              onSearchChange={setSearch}
              activityFilter={activityFilter}
              onActivityFilterChange={setActivityFilter}
              marginBand={marginBand}
              onMarginBandChange={setMarginBand}
            />

            {products.length === 0 ? (
              <Center h={200} mt="md">
                <Stack align="center" gap="sm">
                  <IconChartBar size={48} color="var(--mantine-color-gray-4)" />
                  <Text c="dimmed" size="lg" fw={500}>
                    {hasActiveTableFilters
                      ? 'No products match your filters.'
                      : 'No products yet.'}
                  </Text>
                  {hasActiveTableFilters && (
                    <Text c="dimmed" size="sm">
                      Try adjusting search, margin band, or activity filters.
                    </Text>
                  )}
                </Stack>
              </Center>
            ) : (
              <>
                <Table striped highlightOnHover mt="md">
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Product</Table.Th>
                      <Table.Th>SKU</Table.Th>
                      <Table.Th>Qty Purchased</Table.Th>
                      <Table.Th>Qty Sold</Table.Th>
                      <Table.Th>Revenue</Table.Th>
                      <Table.Th>COGS</Table.Th>
                      <Table.Th>Profit</Table.Th>
                      <Table.Th>Profit Margin</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {products.map((product) => {
                      const marginColor = getMarginColor(product.margin)
                      const marginNum = Number(product.margin)

                      return (
                        <Table.Tr key={product.id}>
                          <Table.Td fw={500}>{product.name}</Table.Td>
                          <Table.Td><Badge variant="outline" color="gray">{product.sku}</Badge></Table.Td>
                          <Table.Td>{formatQuantity(product.qty_purchased)} {product.unit_of_measure}</Table.Td>
                          <Table.Td>{formatQuantity(product.qty_sold)} {product.unit_of_measure}</Table.Td>
                          <Table.Td>{formatCurrency(product.revenue)}</Table.Td>
                          <Table.Td>{formatCurrency(product.cogs)}</Table.Td>
                          <Table.Td fw={600} c={Number(product.profit) < 0 ? 'red' : 'green'}>
                            {formatCurrency(product.profit)}
                          </Table.Td>
                          <Table.Td>
                            <Group justify="space-between" mb={4}>
                              <Text size="sm" fw={500}>{formatMarginPercent(product.margin)}</Text>
                            </Group>
                            <Progress value={marginNum} color={marginColor} size="sm" radius="xl" />
                          </Table.Td>
                        </Table.Tr>
                      )
                    })}
                  </Table.Tbody>
                </Table>

                <div ref={ref} className="mt-2.5 h-5">
                  {isFetchingNextPage && (
                    <Center>
                      <Text size="sm" c="dimmed">Loading more...</Text>
                    </Center>
                  )}
                </div>
              </>
            )}
        </Paper>
      </Stack>
    </Stack>
  )
}
