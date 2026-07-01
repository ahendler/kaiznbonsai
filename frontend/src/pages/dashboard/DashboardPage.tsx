import { useEffect, useState } from 'react'
import {
  SimpleGrid, Card, Text, Group, Center, Loader,
  Table, Progress, Badge, Title, ThemeIcon, Stack, Paper, Box,
} from '@mantine/core'
import {
  IconCash, IconTrendingUp, IconTrendingDown, IconPackage,
} from '@tabler/icons-react'
import { notifications } from '@mantine/notifications'
import { useOverallFinancials, useProductFinancials } from '@/api/financials'
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
  const periodParams = toFinancialPeriodParams(period)
  const periodActive = isFinancialPeriodActive(period)
  const periodLabel = formatFinancialPeriodLabel(period)

  const {
    data: overall,
    isLoading: overallLoading,
    isFetching: overallFetching,
    isError: overallError,
    error: overallErrorObj,
  } = useOverallFinancials(periodParams)

  const {
    data: products,
    isLoading: productsLoading,
    isFetching: productsFetching,
    isError: productsError,
    error: productsErrorObj,
  } = useProductFinancials(periodParams)

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

  const initialLoading = (overallLoading || productsLoading) && !overall && !products
  const isRefreshing = overallFetching || productsFetching

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

      <Box pos="relative">
        {isRefreshing && (
          <Center
            pos="absolute"
            inset={0}
            style={{ zIndex: 1, backgroundColor: 'rgba(255, 255, 255, 0.6)' }}
          >
            <Loader size="sm" />
          </Center>
        )}

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

          <Paper shadow="sm" radius="md" p="md" withBorder>
            <Title order={4} mb="md">Product Performance</Title>
            <Table striped highlightOnHover>
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
                {products?.map((product) => {
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
          </Paper>
        </Stack>
      </Box>
    </Stack>
  )
}
