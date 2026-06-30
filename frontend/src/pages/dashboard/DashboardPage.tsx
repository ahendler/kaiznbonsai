import {
  SimpleGrid, Card, Text, Group, Center, Loader,
  Table, Progress, Badge, Title, ThemeIcon, Stack, Paper,
} from '@mantine/core'
import {
  IconCash, IconTrendingUp, IconTrendingDown, IconPackage,
} from '@tabler/icons-react'
import { useOverallFinancials, useProductFinancials } from '@/api/financials'
import { formatCurrency, formatMarginPercent, formatQuantity, getMarginColor } from '@/utils/financials'

export default function DashboardPage() {
  const { data: overall, isLoading: overallLoading } = useOverallFinancials()
  const { data: products, isLoading: productsLoading } = useProductFinancials()

  if (overallLoading || productsLoading) {
    return <Center h="100%"><Loader /></Center>
  }

  const stats = [
    { title: 'Total Revenue', value: formatCurrency(overall?.revenue || 0), icon: IconCash, color: 'blue' },
    { title: 'Gross Profit', value: formatCurrency(overall?.gross_profit || 0), icon: IconTrendingUp, color: 'green' },
    { title: 'COGS', value: formatCurrency(overall?.cogs || 0), icon: IconTrendingDown, color: 'red' },
    { title: 'Inventory Value', value: formatCurrency(overall?.inventory_value || 0), icon: IconPackage, color: 'grape' },
  ]

  return (
    <Stack gap="xl">
      <Group justify="space-between" align="flex-end">
        <div>
          <Title order={2}>Financial Overview</Title>
          <Text c="dimmed" size="sm">High-level metrics and product performance.</Text>
        </div>
        <Badge size="xl" variant="light" color="blue">
          Overall Margin: {formatMarginPercent(overall?.margin || 0)}
        </Badge>
      </Group>

      <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} spacing="lg">
        {stats.map((stat) => (
          <Card key={stat.title} shadow="sm" padding="lg" radius="md" withBorder>
            <Group justify="space-between">
              <Text size="sm" c="dimmed" fw={500} tt="uppercase">
                {stat.title}
              </Text>
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
  )
}
