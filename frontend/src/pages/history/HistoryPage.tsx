import { useEffect, useMemo, useState } from 'react'
import {
  Alert,
  Badge,
  Center,
  Chip,
  Container,
  Group,
  Skeleton,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import { IconHistory, IconInfoCircle, IconSearch } from '@tabler/icons-react'
import { useDebouncedValue, useIntersection } from '@mantine/hooks'
import { useInfiniteQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import FinancialPeriodFilter from '@/components/dashboard/FinancialPeriodFilter'
import OrderReferenceCell from '@/components/orders/OrderReferenceCell'
import {
  listStockMovements,
  stockMovementQueryKey,
  type MovementReason,
  type StockMovementListFilters,
} from '@/api/activity'
import {
  DEFAULT_FINANCIAL_PERIOD,
  formatFinancialPeriodLabel,
  isFinancialPeriodActive,
  isFinancialPeriodReady,
  toFinancialPeriodParams,
  type FinancialPeriod,
} from '@/utils/financialPeriod'
import {
  MOVEMENT_REASON_OPTIONS,
  formatBatchLabel,
  formatSignedDelta,
  getDeltaColor,
  getMovementLabel,
  getMovementReference,
  getOrderDetailPath,
} from '@/utils/activity'

const ALL_REASONS = MOVEMENT_REASON_OPTIONS.map((option) => option.value)

export default function HistoryPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const stockBatchFromUrl = searchParams.get('stock_batch')

  const [period, setPeriod] = useState<FinancialPeriod>(DEFAULT_FINANCIAL_PERIOD)
  const [search, setSearch] = useState('')
  const [selectedReasons, setSelectedReasons] = useState<MovementReason[]>(ALL_REASONS)
  const [debouncedSearch] = useDebouncedValue(search, 300)

  const periodReady = isFinancialPeriodReady(period)
  const periodParams = periodReady ? toFinancialPeriodParams(period) : {}
  const periodActive = isFinancialPeriodActive(period)
  const periodLabel = formatFinancialPeriodLabel(period)
  const customPeriodIncomplete = period.preset === 'custom' && !periodReady

  const listFilters: StockMovementListFilters = useMemo(
    () => ({
      ...periodParams,
      search: debouncedSearch,
      ...(stockBatchFromUrl ? { stock_batch: stockBatchFromUrl } : {}),
      ...(selectedReasons.length > 0 && selectedReasons.length < ALL_REASONS.length
        ? { reason: selectedReasons }
        : {}),
    }),
    [periodParams, debouncedSearch, stockBatchFromUrl, selectedReasons],
  )

  const hasActiveFilters = Boolean(
    debouncedSearch
    || stockBatchFromUrl
    || periodActive
    || (selectedReasons.length > 0 && selectedReasons.length < ALL_REASONS.length),
  )

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    status,
  } = useInfiniteQuery({
    queryKey: stockMovementQueryKey(listFilters),
    queryFn: ({ pageParam }) => listStockMovements(pageParam as string | null, listFilters),
    initialPageParam: null as string | null,
    enabled: periodReady,
    getNextPageParam: (lastPage) => {
      if (!lastPage.next) return null
      const url = new URL(lastPage.next)
      return url.searchParams.get('cursor')
    },
  })

  const movements = data?.pages.flatMap((page) => page.results) ?? []

  const { ref, entry } = useIntersection({ threshold: 1 })

  useEffect(() => {
    if (entry?.isIntersecting && hasNextPage && !isFetchingNextPage) {
      fetchNextPage()
    }
  }, [entry?.isIntersecting, hasNextPage, isFetchingNextPage, fetchNextPage])

  const toggleReason = (reason: MovementReason) => {
    setSelectedReasons((current) => {
      if (current.includes(reason)) {
        const next = current.filter((value) => value !== reason)
        return next.length === 0 ? ALL_REASONS : next
      }
      return [...current, reason]
    })
  }

  const clearBatchFilter = () => {
    const next = new URLSearchParams(searchParams)
    next.delete('stock_batch')
    setSearchParams(next, { replace: true })
  }

  const activeFilterSummary = [
    periodLabel,
    stockBatchFromUrl ? 'This batch only' : null,
    selectedReasons.length > 0 && selectedReasons.length < ALL_REASONS.length
      ? selectedReasons.map(getMovementLabel).join(', ')
      : null,
    debouncedSearch ? `Search: ${debouncedSearch}` : null,
  ].filter(Boolean)

  return (
    <Container size="xl" p={0}>
      <Group gap="sm" align="baseline" mb="lg" wrap="wrap">
        <Title order={2}>Stock History</Title>
        <Text c="dimmed" size="sm">
          received, sold, returned, voided, and corrected
        </Text>
      </Group>

      <Stack gap="md" mb="md">
        <Group align="flex-end" wrap="wrap" gap="md">
          <FinancialPeriodFilter value={period} onChange={setPeriod} />
          <TextInput
            className="min-w-[220px] flex-1"
            placeholder="Search product, lot, or order"
            leftSection={<IconSearch size={16} />}
            value={search}
            onChange={(event) => setSearch(event.currentTarget.value)}
          />
        </Group>

        <Group gap="xs" wrap="wrap">
          {MOVEMENT_REASON_OPTIONS.map((option) => (
            <Chip
              key={option.value}
              checked={selectedReasons.includes(option.value)}
              onChange={() => toggleReason(option.value)}
              variant="light"
            >
              {option.label}
            </Chip>
          ))}
        </Group>

        {hasActiveFilters && activeFilterSummary.length > 0 && (
          <Group gap="xs">
            {activeFilterSummary.map((label) => (
              <Badge key={label} variant="light" color="gray">
                {label}
              </Badge>
            ))}
            {stockBatchFromUrl && (
              <Badge
                variant="light"
                color="blue"
                className="cursor-pointer"
                onClick={clearBatchFilter}
              >
                Clear batch filter ×
              </Badge>
            )}
          </Group>
        )}
      </Stack>

      {customPeriodIncomplete ? (
        <Center h={200}>
          <Text c="dimmed">Select a start and end date for the custom range.</Text>
        </Center>
      ) : status === 'pending' ? (
        <Stack gap="sm">
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} height={50} radius="md" />
          ))}
        </Stack>
      ) : status === 'error' ? (
        <Center h={200}>
          <Text c="red">Error loading activity history.</Text>
        </Center>
      ) : movements.length === 0 ? (
        <Center h={300}>
          <Stack align="center" gap="sm">
            <IconHistory size={48} color="var(--mantine-color-gray-4)" />
            <Text c="dimmed" size="lg" fw={500}>
              {hasActiveFilters ? 'No activity matches your filters' : 'No activity yet'}
            </Text>
            <Text c="dimmed" size="sm" ta="center" maw={420}>
              {hasActiveFilters
                ? 'Try adjusting the period, event type, or search terms.'
                : 'Confirm purchase or sales orders, void manual batches, or cancel orders to see stock movements here.'}
            </Text>
          </Stack>
        </Center>
      ) : (
        <>
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>When</Table.Th>
                <Table.Th>Event</Table.Th>
                <Table.Th>Product</Table.Th>
                <Table.Th>Batch</Table.Th>
                <Table.Th>Change</Table.Th>
                <Table.Th>Reference</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {movements.map((movement) => {
                const reference = getMovementReference(movement)
                const orderStatus = movement.sales_order?.status ?? movement.purchase_order?.status
                const orderPath = getOrderDetailPath(movement)

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
                      <Text size="sm" fw={500}>{movement.product.name}</Text>
                      <Text size="xs" c="dimmed">{movement.product.sku}</Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm">
                        {formatBatchLabel(movement.stock_batch.lot_code, movement.stock_batch.id)}
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
                        orderPath={orderPath}
                        orderStatus={orderStatus}
                      />
                    </Table.Td>
                  </Table.Tr>
                )
              })}
            </Table.Tbody>
          </Table>

          <div ref={ref} className="h-4" />

          {isFetchingNextPage && (
            <Center py="md">
              <Text size="sm" c="dimmed">Loading more…</Text>
            </Center>
          )}
        </>
      )}

      <Alert
        mt="xl"
        variant="light"
        color="blue"
        icon={<IconInfoCircle size={16} />}
        title="Audit trail"
      >
        Cancelled sales and purchase orders remain listed for traceability. Dashboard revenue and COGS
        exclude cancelled orders; qty purchased and qty sold net reversals within the selected period.
      </Alert>
    </Container>
  )
}
