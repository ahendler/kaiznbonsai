import { useState, useEffect } from 'react'
import {
  Drawer,
  Stack,
  Text,
  Group,
  Button,
  TextInput,
  NumberInput,
  Table,
  ActionIcon,
  Paper,
  Badge,
  Center,
  Tooltip,
  Box,
  Modal,
} from '@mantine/core'
import { useForm, isNotEmpty } from '@mantine/form'
import { useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { notifications } from '@mantine/notifications'
import { IconTrash, IconEdit, IconCheck, IconX, IconHistory } from '@tabler/icons-react'
import { listStocks, createStock, updateStock, voidStock } from '@/api/inventory'
import type { StockUpdatePayload } from '@/api/inventory'
import { invalidateFinancials } from '@/api/financials'
import { getApiErrorMessage, getFormErrorsFromApi, getAxiosResponseData } from '@/api/errors'
import BatchActivityPanel from '@/components/inventory/BatchActivityPanel'

interface StockFormValues {
  initial_quantity: string
  unit_cost: string
  lot_code: string
  best_before: string
}

interface StockDrawerProps {
  opened: boolean
  onClose: () => void
  productId: string
  productName: string
}

export default function StockDrawer({ opened, onClose, productId, productName }: StockDrawerProps) {
  const queryClient = useQueryClient()
  
  const { data, fetchNextPage, hasNextPage, isFetchingNextPage } = useInfiniteQuery({
    queryKey: ['stocks', productId],
    queryFn: ({ pageParam }) => listStocks(productId, pageParam as string | null),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => {
      if (!lastPage.next) return null
      const url = new URL(lastPage.next)
      return url.searchParams.get('cursor')
    },
    enabled: opened && !!productId,
  })

  const form = useForm<StockFormValues>({
    initialValues: {
      initial_quantity: '',
      unit_cost: '',
      lot_code: '',
      best_before: '',
    },
    validate: {
      initial_quantity: isNotEmpty('Quantity is required'),
      unit_cost: isNotEmpty('Unit cost is required'),
    },
  })

  const createMutation = useMutation({
    mutationFn: (values: StockFormValues) => createStock({
      product: productId,
      initial_quantity: values.initial_quantity.toString(),
      current_quantity: values.initial_quantity.toString(),
      unit_cost: values.unit_cost.toString(),
      lot_code: values.lot_code || undefined,
      best_before: values.best_before || undefined,
    }),
    onSuccess: () => {
      notifications.show({ title: 'Success', message: 'Batch added successfully', color: 'green' })
      queryClient.invalidateQueries({ queryKey: ['stocks', productId] })
      queryClient.invalidateQueries({ queryKey: ['products'] })
      queryClient.invalidateQueries({ queryKey: ['stock-batch-movements'] })
      queryClient.invalidateQueries({ queryKey: ['stock-movements'] })
      invalidateFinancials(queryClient)
      form.reset()
    },
    onError: (error) => {
      const formErrors = getFormErrorsFromApi(getAxiosResponseData(error))
      if (formErrors) {
        form.setErrors(formErrors)
      } else {
        notifications.show({ title: 'Error', message: 'Failed to add batch. Check your inputs.', color: 'red' })
      }
    }
  })

  const voidMutation = useMutation({
    mutationFn: (id: string) => voidStock(id),
    onSuccess: () => {
      notifications.show({ title: 'Success', message: 'Batch voided successfully', color: 'green' })
      queryClient.invalidateQueries({ queryKey: ['stocks', productId] })
      queryClient.invalidateQueries({ queryKey: ['products'] })
      queryClient.invalidateQueries({ queryKey: ['stock-batch-movements'] })
      queryClient.invalidateQueries({ queryKey: ['stock-movements'] })
      invalidateFinancials(queryClient)
    },
    onError: (error) => {
      notifications.show({ title: 'Error', message: getApiErrorMessage(error, 'Failed to void batch.'), color: 'red' })
    }
  })

  // Edit State
  const [editingStockId, setEditingStockId] = useState<string | null>(null)
  const [expandedBatchId, setExpandedBatchId] = useState<string | null>(null)
  const [batchToVoid, setBatchToVoid] = useState<string | null>(null)
  const [editValues, setEditValues] = useState<{
    lot_code: string
    initial_quantity: number | ''
    unit_cost: number | ''
    best_before: string
  }>({
    lot_code: '',
    initial_quantity: '',
    unit_cost: '',
    best_before: '',
  })
  
  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string, payload: StockUpdatePayload }) => updateStock(id, payload),
    onSuccess: () => {
      notifications.show({ title: 'Success', message: 'Batch updated', color: 'green' })
      queryClient.invalidateQueries({ queryKey: ['stocks', productId] })
      queryClient.invalidateQueries({ queryKey: ['products'] })
      queryClient.invalidateQueries({ queryKey: ['stock-batch-movements'] })
      queryClient.invalidateQueries({ queryKey: ['stock-movements'] })
      invalidateFinancials(queryClient)
      setEditingStockId(null)
    },
    onError: (error) => {
      notifications.show({ title: 'Error', message: getApiErrorMessage(error, 'Failed to update batch.'), color: 'red' })
    }
  })

  const stocks = data?.pages.flatMap((page) => page.results) ?? []

  useEffect(() => {
    if (!opened) {
      setExpandedBatchId(null)
      setEditingStockId(null)
    }
  }, [opened])

  return (
    <Drawer
      opened={opened}
      onClose={onClose}
      position="right"
      size="xl"
      title={
        <Group>
          <Text fw={600} size="lg">Manage Stock</Text>
          <Badge variant="light" color="blue">{productName}</Badge>
        </Group>
      }
    >
      <Stack gap="xl">
        <Paper withBorder p="md" radius="md">
          <Text fw={500} mb="sm">Add New Batch</Text>
          <form onSubmit={form.onSubmit((values) => createMutation.mutate(values))}>
            <Group align="flex-start" grow>
              <NumberInput
                label="Initial Quantity"
                placeholder="100"
                min={0}
                hideControls
                {...form.getInputProps('initial_quantity')}
              />
              <NumberInput
                label="Unit Cost ($)"
                placeholder="1.50"
                min={0}
                decimalScale={2}
                hideControls
                {...form.getInputProps('unit_cost')}
              />
            </Group>
            <Group align="flex-start" grow mt="sm">
              <TextInput
                label="Lot Code"
                placeholder="LOT-123"
                {...form.getInputProps('lot_code')}
              />
              <TextInput
                label="Best Before"
                type="date"
                {...form.getInputProps('best_before')}
              />
            </Group>
            <Group justify="flex-end" mt="md">
              <Button type="submit" loading={createMutation.isPending} color="green">
                Add Batch
              </Button>
            </Group>
          </form>
        </Paper>

        <div>
          <Text fw={500} mb="sm">Current Batches</Text>
          <div style={{ overflowX: 'auto' }}>
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Lot Code</Table.Th>
                  <Table.Th>Initial Qty</Table.Th>
                  <Table.Th>Remaining Qty</Table.Th>
                  <Table.Th>Cost</Table.Th>
                  <Table.Th>Best Before</Table.Th>
                  <Table.Th>Actions</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {stocks.length === 0 ? (
                  <Table.Tr>
                    <Table.Td colSpan={6}>
                      <Text c="dimmed" ta="center">No stock batches found.</Text>
                    </Table.Td>
                  </Table.Tr>
                ) : (
                  stocks.map((stock) => {
                    const isEditing = editingStockId === stock.id
                    const isConsumed = parseFloat(stock.current_quantity) < parseFloat(stock.initial_quantity)
                    
                    return (
                      <>
                      <Table.Tr key={stock.id}>
                        <Table.Td>
                          {isEditing ? (
                            <TextInput
                              size="xs"
                              value={editValues.lot_code}
                              onChange={(e) => setEditValues({ ...editValues, lot_code: e.currentTarget.value })}
                              styles={{ input: { width: 100 } }}
                            />
                          ) : stock.lot_code ? (
                            <Badge variant="outline" color="gray">{stock.lot_code}</Badge>
                          ) : '-'}
                        </Table.Td>
                        <Table.Td>
                          {isEditing ? (
                            <NumberInput
                              size="xs"
                              value={editValues.initial_quantity}
                              onChange={(val) => setEditValues({ ...editValues, initial_quantity: typeof val === 'number' ? val : parseFloat(val) || 0 })}
                              disabled={isConsumed}
                              hideControls
                              styles={{ input: { width: 80 } }}
                              min={0}
                            />
                          ) : (
                            <Text>{parseFloat(stock.initial_quantity)}</Text>
                          )}
                        </Table.Td>
                        <Table.Td>
                          <Text fw={500}>
                            {parseFloat(stock.current_quantity)}
                          </Text>
                        </Table.Td>
                        <Table.Td>
                          {isEditing ? (
                            <NumberInput
                              size="xs"
                              value={editValues.unit_cost}
                              onChange={(val) => setEditValues({ ...editValues, unit_cost: typeof val === 'number' ? val : parseFloat(val) || 0 })}
                              decimalScale={2}
                              hideControls
                              styles={{ input: { width: 80 } }}
                              min={0}
                            />
                          ) : (
                            <Text>${parseFloat(stock.unit_cost).toFixed(2)}</Text>
                          )}
                        </Table.Td>
                        <Table.Td>
                          {isEditing ? (
                            <TextInput
                              type="date"
                              size="xs"
                              value={editValues.best_before}
                              onChange={(e) => setEditValues({ ...editValues, best_before: e.currentTarget.value })}
                              styles={{ input: { width: 130 } }}
                            />
                          ) : (
                            <Text>{stock.best_before || '-'}</Text>
                          )}
                        </Table.Td>
                        <Table.Td>
                          {isEditing ? (
                            <Group gap="xs" wrap="nowrap">
                              <ActionIcon
                                color="green"
                                variant="light"
                                loading={updateMutation.isPending}
                                onClick={() => {
                                  if (editValues.initial_quantity !== '' && editValues.unit_cost !== '') {
                                    const payload: StockUpdatePayload = {
                                      lot_code: editValues.lot_code || undefined,
                                      initial_quantity: editValues.initial_quantity.toString(),
                                      unit_cost: editValues.unit_cost.toString(),
                                      best_before: editValues.best_before || null,
                                    }
                                    if (!isConsumed) {
                                      payload.current_quantity = editValues.initial_quantity.toString()
                                    }
                                    updateMutation.mutate({ id: stock.id, payload })
                                  }
                                }}
                              >
                                <IconCheck size={16} />
                              </ActionIcon>
                              <ActionIcon
                                color="gray"
                                variant="light"
                                onClick={() => setEditingStockId(null)}
                              >
                                <IconX size={16} />
                              </ActionIcon>
                            </Group>
                          ) : (
                            <Group gap="xs" wrap="nowrap">
                              <Tooltip label={expandedBatchId === stock.id ? 'Hide activity' : 'Show activity'}>
                                <ActionIcon
                                  color={expandedBatchId === stock.id ? 'green' : 'gray'}
                                  variant={expandedBatchId === stock.id ? 'light' : 'subtle'}
                                  onClick={() => {
                                    setExpandedBatchId((current) => (
                                      current === stock.id ? null : stock.id
                                    ))
                                  }}
                                >
                                  <IconHistory size={16} />
                                </ActionIcon>
                              </Tooltip>
                              <ActionIcon
                                color="blue"
                                variant="subtle"
                                onClick={() => {
                                  setEditingStockId(stock.id)
                                  setEditValues({
                                    lot_code: stock.lot_code || '',
                                    initial_quantity: parseFloat(stock.initial_quantity),
                                    unit_cost: parseFloat(stock.unit_cost),
                                    best_before: stock.best_before || '',
                                  })
                                }}
                              >
                                <IconEdit size={16} />
                              </ActionIcon>
                              {stock.is_po_linked ? (
                                <Tooltip label="Cancel the purchase order to reverse receipt.">
                                  <Box display="inline-block">
                                    <ActionIcon
                                      color="gray"
                                      variant="subtle"
                                      disabled
                                      style={{ pointerEvents: 'none' }}
                                    >
                                      <IconTrash size={16} />
                                    </ActionIcon>
                                  </Box>
                                </Tooltip>
                              ) : isConsumed ? (
                                <Tooltip label="Cannot void a partially or fully consumed batch">
                                  <Box display="inline-block">
                                    <ActionIcon
                                      color="gray"
                                      variant="subtle"
                                      disabled
                                      style={{ pointerEvents: 'none' }}
                                    >
                                      <IconTrash size={16} />
                                    </ActionIcon>
                                  </Box>
                                </Tooltip>
                              ) : (
                                <Tooltip label="Void batch">
                                  <ActionIcon
                                    color="red"
                                    variant="subtle"
                                    onClick={() => setBatchToVoid(stock.id)}
                                  >
                                    <IconTrash size={16} />
                                  </ActionIcon>
                                </Tooltip>
                              )}
                            </Group>
                          )}
                        </Table.Td>
                      </Table.Tr>
                      {expandedBatchId === stock.id && (
                        <Table.Tr>
                          <Table.Td colSpan={6} p={0}>
                            <BatchActivityPanel batchId={stock.id} />
                          </Table.Td>
                        </Table.Tr>
                      )}
                      </>
                    )
                  })
                )}
              </Table.Tbody>
            </Table>
          </div>
          {hasNextPage && (
            <Center mt="md">
              <Button variant="subtle" onClick={() => fetchNextPage()} loading={isFetchingNextPage}>
                Load More
              </Button>
            </Center>
          )}
        </div>
      </Stack>

      <Modal
        opened={!!batchToVoid}
        onClose={() => setBatchToVoid(null)}
        title="Void stock batch"
        centered
      >
        <Stack gap="md">
          <Text size="sm">
            This voids the batch and records the removal in stock history. It cannot be undone.
          </Text>
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setBatchToVoid(null)}>Cancel</Button>
            <Button
              color="red"
              loading={voidMutation.isPending}
              onClick={() => {
                if (batchToVoid) {
                  voidMutation.mutate(batchToVoid, {
                    onSuccess: () => setBatchToVoid(null),
                  })
                }
              }}
            >
              Void batch
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Drawer>
  )
}
