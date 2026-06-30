import { useEffect, useRef, useState } from 'react'
import {
  Container,
  Group,
  Title,
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
  Box,
} from '@mantine/core'
import type { TextProps } from '@mantine/core'
import { useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { notifications } from '@mantine/notifications'
import { useIntersection } from '@mantine/hooks'
import {
  IconPlus,
  IconEdit,
  IconTrash,
  IconBoxSeam,
  IconCopy,
  IconCheck,
} from '@tabler/icons-react'
import { listProducts, deleteProduct } from '@/api/inventory'
import type { Product } from '@/api/inventory'
import { useDisclosure } from '@mantine/hooks'
import ProductFormModal from '@/components/inventory/ProductFormModal'
import StockDrawer from '@/components/inventory/StockDrawer'

const CopyAction = ({ value }: { value: string }) => (
  <CopyButton value={value} timeout={2000}>
    {({ copied, copy }) => (
      <Tooltip label={copied ? 'Copied' : 'Copy'} withArrow position="right">
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
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    status,
  } = useInfiniteQuery({
    queryKey: ['products', 'infinite'],
    queryFn: ({ pageParam }) => listProducts(pageParam as string | null),
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
    onError: () => {
      notifications.show({
        title: 'Error',
        message: 'Failed to delete product. It may have existing stock batches.',
        color: 'red',
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

  return (
    <Container size="xl" p={0}>
      <Group justify="space-between" mb="lg">
        <Title order={2}>Products</Title>
        <Button
          leftSection={<IconPlus size={16} />}
          color="green"
          onClick={handleAddProduct}
        >
          Add Product
        </Button>
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
              No products found
            </Text>
            <Text c="dimmed" size="sm">
              Get started by adding your first product.
            </Text>
            <Button
              variant="light"
              color="green"
              mt="sm"
              onClick={handleAddProduct}
            >
              Add Product
            </Button>
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
                      <CopyAction value={product.name} />
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
                      {parseFloat(product.total_stock || '0') > 0 ? (
                        <Tooltip label="Cannot delete a product with active stock batches. Remove all stock first.">
                          <Box display="inline-block">
                            <ActionIcon
                              variant="subtle"
                              color="gray"
                              disabled
                              className="pointer-events-none"
                            >
                              <IconTrash size={16} />
                            </ActionIcon>
                          </Box>
                        </Tooltip>
                      ) : (
                        <Tooltip label="Delete product">
                          <ActionIcon
                            variant="subtle"
                            color="red"
                            onClick={() => setProductToDelete(product)}
                          >
                            <IconTrash size={16} />
                          </ActionIcon>
                        </Tooltip>
                      )}
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
          {parseFloat(productToDelete?.total_stock || '0') > 0 && (
            <Text size="sm" c="red" mt="sm">
              You cannot delete a product that currently has stock. Please remove all stock batches first.
            </Text>
          )}
        </Stack>
        <Group justify="flex-end">
          <Button variant="default" onClick={() => setProductToDelete(null)} disabled={deleteMutation.isPending}>
            Cancel
          </Button>
          <Button
            color="red"
            loading={deleteMutation.isPending}
            disabled={parseFloat(productToDelete?.total_stock || '0') > 0}
            onClick={() => productToDelete && deleteMutation.mutate(productToDelete.id)}
          >
            Delete
          </Button>
        </Group>
      </Modal>

      <StockDrawer
        opened={!!stockProduct}
        onClose={() => setStockProduct(null)}
        productId={stockProduct?.id || ''}
        productName={stockProduct?.name || ''}
      />
    </Container>
  )
}
