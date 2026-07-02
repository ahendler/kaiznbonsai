import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Container,
  Group,
  Button,
  Table,
  Badge,
  ActionIcon,
  Text,
  Center,
  Skeleton,
  Stack,
  Tooltip,
  CopyButton,
  Modal,
  TextInput,
  Select,
  Popover,
  Checkbox,
  Input,
} from '@mantine/core'
import type { TextProps } from '@mantine/core'
import { useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { notifications } from '@mantine/notifications'
import { useDebouncedValue, useDisclosure, useIntersection } from '@mantine/hooks'
import {
  IconPlus,
  IconEdit,
  IconBoxSeam,
  IconCopy,
  IconCheck,
  IconSearch,
  IconChevronDown,
} from '@tabler/icons-react'
import { listProducts, deleteProduct } from '@/api/inventory'
import type { Product, ProductListFilters } from '@/api/inventory'
import { getApiErrorMessage } from '@/api/errors'
import ProductFormModal from '@/components/inventory/ProductFormModal'
import StockDrawer from '@/components/inventory/StockDrawer'
import { PageTitle } from '@/components/layout/PageTitle'

const UNIT_FILTER_OPTIONS = [
  { value: 'KG', label: 'Kilogram (KG)' },
  { value: 'G', label: 'Gram (G)' },
  { value: 'L', label: 'Liter (L)' },
  { value: 'ML', label: 'Milliliter (mL)' },
  { value: 'UNIT', label: 'Unit' },
] as const

type UnitOfMeasure = Product['unit_of_measure']

function unitFilterButtonLabel(selected: UnitOfMeasure[]): string {
  if (selected.length === 0) {
    return 'All units'
  }
  if (selected.length === 1) {
    return UNIT_FILTER_OPTIONS.find((option) => option.value === selected[0])?.label ?? selected[0]
  }
  return `${selected.length} units`
}

type StockFilter = 'all' | 'in_stock' | 'out_of_stock'

function parseStockFilter(value: string | null): StockFilter {
  if (value === 'out_of_stock') return 'out_of_stock'
  if (value === 'in_stock') return 'in_stock'
  return 'all'
}

const STOCK_FILTER_OPTIONS = [
  { value: 'all', label: 'All stock' },
  { value: 'in_stock', label: 'In stock only' },
  { value: 'out_of_stock', label: 'Out of stock only' },
] as const

const CopyAction = ({
  value,
  copyLabel = 'Copy',
  copiedLabel = 'Copied',
}: {
  value: string
  copyLabel?: string
  copiedLabel?: string
}) => (
  <CopyButton value={value} timeout={2000}>
    {({ copied, copy }) => (
      <Tooltip label={copied ? copiedLabel : copyLabel} withArrow position="right">
        <ActionIcon color={copied ? 'teal' : 'gray'} variant="subtle" onClick={copy} size="xs">
          {copied ? <IconCheck size={14} /> : <IconCopy size={14} />}
        </ActionIcon>
      </Tooltip>
    )}
  </CopyButton>
)

const TruncatedTextWithTooltip = ({
  text,
  multiline,
  tooltipWidth,
  ...props
}: {
  text: string
  multiline?: boolean
  tooltipWidth?: number
} & TextProps) => {
  const ref = useRef<HTMLDivElement>(null)
  const [isTruncated, setIsTruncated] = useState(false)
  const maxWidth = tooltipWidth ?? 320

  return (
    <Tooltip
      withArrow
      disabled={!isTruncated}
      multiline={multiline}
      maw={multiline ? maxWidth : undefined}
      label={
        multiline ? (
          <Text size="sm" style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
            {text}
          </Text>
        ) : (
          text
        )
      }
    >
      <Text
        ref={ref}
        truncate="end"
        onMouseEnter={() => {
          if (ref.current) {
            setIsTruncated(ref.current.scrollWidth > ref.current.clientWidth)
          }
        }}
        {...props}
      >
        {text}
      </Text>
    </Tooltip>
  )
}

export default function ProductListPage() {
  const [searchParams] = useSearchParams()
  const [search, setSearch] = useState('')
  const [unitFilters, setUnitFilters] = useState<UnitOfMeasure[]>([])
  const [stockFilter, setStockFilter] = useState<StockFilter>(() =>
    parseStockFilter(searchParams.get('stock')),
  )
  const [debouncedSearch] = useDebouncedValue(search, 300)

  const listFilters: ProductListFilters = {
    search: debouncedSearch,
    ...(unitFilters.length > 0 ? { unit_of_measure: unitFilters } : {}),
    ...(stockFilter === 'in_stock' ? { in_stock: true } : {}),
    ...(stockFilter === 'out_of_stock' ? { in_stock: false } : {}),
  }

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    status,
  } = useInfiniteQuery({
    queryKey: ['products', 'infinite', listFilters],
    queryFn: ({ pageParam }) => listProducts(pageParam as string | null, listFilters),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => {
      if (!lastPage.next) return null
      const url = new URL(lastPage.next)
      return url.searchParams.get('cursor')
    },
  })

  // Modal state
  const queryClient = useQueryClient()
  const [modalOpened, { open: openModal, close: closeModal }] = useDisclosure(false)
  const [editingProduct, setEditingProduct] = useState<Product | null>(null)
  const [productToDelete, setProductToDelete] = useState<Product | null>(null)
  const [stockProduct, setStockProduct] = useState<Product | null>(null)

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteProduct(id),
    onSuccess: () => {
      notifications.show({
        title: 'Success',
        message: 'Product deleted successfully',
        color: 'green',
      })
      queryClient.invalidateQueries({ queryKey: ['products'] })
      setProductToDelete(null)
    },
    onError: (error) => {
      notifications.show({
        title: 'Cannot delete product',
        message: getApiErrorMessage(
          error,
          'Failed to delete product. Stock batch history may still exist for traceability.',
        ),
        color: 'red',
        autoClose: 8000,
      })
    },
  })

  const handleAddProduct = () => {
    setEditingProduct(null)
    openModal()
  }

  const handleEditProduct = (product: Product) => {
    setEditingProduct(product)
    openModal()
  }

  // Intersection observer for infinite scrolling
  const { ref, entry } = useIntersection({
    threshold: 1,
  })

  useEffect(() => {
    if (entry?.isIntersecting && hasNextPage && !isFetchingNextPage) {
      fetchNextPage()
    }
  }, [entry?.isIntersecting, hasNextPage, isFetchingNextPage, fetchNextPage])

  const products = data?.pages.flatMap((page) => page.results) ?? []
  const hasActiveFilters = Boolean(debouncedSearch || unitFilters.length > 0 || stockFilter !== 'all')

  return (
    <Container size="xl" p={0}>
      <Group justify="space-between" align="baseline" mb="lg" wrap="wrap">
        <PageTitle
          title="Products"
          subtitle="catalog, stock levels, and units of measure"
        />
        <Button
          leftSection={<IconPlus size={16} />}
          color="green"
          onClick={handleAddProduct}
        >
          Add Product
        </Button>
      </Group>

      <Group align="flex-end" mb="md" wrap="wrap" gap="md">
        <TextInput
          className="min-w-[220px] flex-1"
          placeholder="Search by name or SKU"
          leftSection={<IconSearch size={16} />}
          value={search}
          onChange={(e) => setSearch(e.currentTarget.value)}
        />
        <Popover width={220} position="bottom-start" withArrow shadow="md">
          <Popover.Target>
            <Input
              component="button"
              type="button"
              pointer
              className="w-[180px]"
              rightSection={<IconChevronDown size={16} stroke={1.5} />}
              rightSectionPointerEvents="none"
            >
              <Text size="sm" truncate>
                {unitFilterButtonLabel(unitFilters)}
              </Text>
            </Input>
          </Popover.Target>
          <Popover.Dropdown>
            <Checkbox.Group
              value={unitFilters}
              onChange={(value) => setUnitFilters(value as UnitOfMeasure[])}
            >
              <Stack gap="xs">
                {UNIT_FILTER_OPTIONS.map((option) => (
                  <Checkbox
                    key={option.value}
                    value={option.value}
                    label={option.label}
                  />
                ))}
              </Stack>
            </Checkbox.Group>
            {unitFilters.length > 0 && (
              <Button
                variant="subtle"
                size="compact-xs"
                mt="sm"
                onClick={() => setUnitFilters([])}
              >
                Clear units
              </Button>
            )}
          </Popover.Dropdown>
        </Popover>
        <Select
          className="w-[200px]"
          data={[...STOCK_FILTER_OPTIONS]}
          value={stockFilter}
          onChange={(value) => setStockFilter((value as StockFilter | null) ?? 'all')}
        />
      </Group>

      {status === 'pending' ? (
        <Stack gap="sm">
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} height={50} radius="md" />
          ))}
        </Stack>
      ) : status === 'error' ? (
        <Center h={200}>
          <Text c="red">Error loading products.</Text>
        </Center>
      ) : products.length === 0 ? (
        <Center h={300}>
          <Stack align="center" gap="sm">
            <IconBoxSeam size={48} color="var(--mantine-color-gray-4)" />
            <Text c="dimmed" size="lg" fw={500}>
              {hasActiveFilters ? 'No products match your filters' : 'No products found'}
            </Text>
            <Text c="dimmed" size="sm">
              {hasActiveFilters
                ? 'Try adjusting search, unit, or stock filters.'
                : 'Get started by adding your first product.'}
            </Text>
            {!hasActiveFilters && (
              <Button
                variant="light"
                color="green"
                mt="sm"
                onClick={handleAddProduct}
              >
                Add Product
              </Button>
            )}
          </Stack>
        </Center>
      ) : (
        <div className="overflow-x-auto">
          <Table verticalSpacing="sm" striped highlightOnHover withColumnBorders>
            <Table.Thead>
              <Table.Tr>
                <Table.Th className="w-full">Name</Table.Th>
                <Table.Th className="whitespace-nowrap">SKU</Table.Th>
                <Table.Th ta="center" className="whitespace-nowrap">Unit</Table.Th>
                <Table.Th ta="center" className="whitespace-nowrap">Total Stock</Table.Th>
                <Table.Th ta="center" className="whitespace-nowrap">Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {products.map((product) => (
                <Table.Tr key={product.id}>
                  <Table.Td className="max-w-[250px]">
                    <Group gap="xs" wrap="nowrap">
                      <div className="min-w-0 flex-1">
                        <TruncatedTextWithTooltip text={product.name} fw={500} />
                        {product.description && (
                          <TruncatedTextWithTooltip
                            text={product.description}
                            size="xs"
                            c="dimmed"
                            multiline
                            tooltipWidth={360}
                          />
                        )}
                      </div>
                      <CopyAction value={product.name} copyLabel="Copy product name" />
                    </Group>
                  </Table.Td>
                  <Table.Td className="max-w-[200px]">
                    <Group gap="xs" wrap="nowrap">
                      <div className="min-w-0 flex-1">
                        <TruncatedTextWithTooltip 
                          text={product.sku} 
                          size="sm" 
                          c="dimmed" 
                          ff="monospace" 
                        />
                      </div>
                      <CopyAction value={product.sku} />
                    </Group>
                  </Table.Td>
                  <Table.Td ta="center">{product.unit_of_measure}</Table.Td>
                  <Table.Td ta="center">
                    {parseFloat(product.total_stock) === 0 ? (
                      <Text fw={500} c="red">
                        0
                      </Text>
                    ) : (
                      <Text fw={500}>
                        {parseFloat(product.total_stock).toLocaleString()}
                      </Text>
                    )}
                  </Table.Td>
                  <Table.Td>
                    <Group gap="xs" wrap="nowrap" justify="center">
                      <Button
                        variant="light"
                        color="green"
                        size="xs"
                        onClick={() => setStockProduct(product)}
                      >
                        View Stock
                      </Button>
                      <ActionIcon
                        variant="subtle"
                        color="gray"
                        onClick={() => handleEditProduct(product)}
                      >
                        <IconEdit size={16} />
                      </ActionIcon>
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>

          {/* Invisible element at the bottom to trigger infinite scroll */}
          <div ref={ref} className="mt-2.5 h-5">
            {isFetchingNextPage && (
              <Center>
                <Text size="sm" c="dimmed">Loading more...</Text>
              </Center>
            )}
          </div>
        </div>
      )}

      <ProductFormModal
        opened={modalOpened}
        onClose={closeModal}
        product={editingProduct}
        onRequestDelete={(product) => {
          closeModal()
          setProductToDelete(product)
        }}
        onViewStock={(product) => {
          setStockProduct(product)
        }}
      />

      <Modal
        opened={!!productToDelete}
        onClose={() => setProductToDelete(null)}
        title={
          <Badge color="red" variant="light" size="lg" radius="sm">
            Delete Product
          </Badge>
        }
        centered
      >
        <Stack gap="xs" mb="lg">
          <Text size="sm">Are you sure you want to delete:</Text>
          <div className="overflow-hidden">
            <TruncatedTextWithTooltip text={productToDelete?.name || ''} fw={600} />
          </div>
          <Text size="sm" c="dimmed">
            This action cannot be undone.
          </Text>
          {productToDelete?.has_stock_batches && (
            <Text size="sm" c="red" mt="sm">
              This product still has stock batches (including fully consumed). Batch history is
              kept for traceability — use View Stock to review before deleting.
            </Text>
          )}
        </Stack>
        <Group justify="space-between">
          {productToDelete?.has_stock_batches ? (
            <Button
              variant="light"
              color="green"
              onClick={() => {
                setStockProduct(productToDelete)
                setProductToDelete(null)
              }}
            >
              View stock batches
            </Button>
          ) : (
            <span />
          )}
          <Group>
          <Button variant="default" onClick={() => setProductToDelete(null)} disabled={deleteMutation.isPending}>
            Cancel
          </Button>
          <Button
            color="red"
            loading={deleteMutation.isPending}
            disabled={productToDelete?.has_stock_batches}
            onClick={() => productToDelete && deleteMutation.mutate(productToDelete.id)}
          >
            Delete
          </Button>
          </Group>
        </Group>
      </Modal>

      <StockDrawer
        opened={!!stockProduct}
        onClose={() => setStockProduct(null)}
        productId={stockProduct?.id || ''}
        productName={stockProduct?.name || ''}
        hasVoidedBatches={stockProduct?.has_voided_batches ?? false}
      />
    </Container>
  )
}
