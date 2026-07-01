import { useEffect } from 'react'
import { Modal, TextInput, Select, Textarea, Button, Group, Stack, Text, Tooltip, Box } from '@mantine/core'
import { useForm, isNotEmpty } from '@mantine/form'
import { notifications } from '@mantine/notifications'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createProduct, updateProduct } from '@/api/inventory'
import type { Product, ProductCreatePayload } from '@/api/inventory'
import { getApiErrorMessage, getFormErrorsFromApi, getAxiosResponseData } from '@/api/errors'

const DELETE_BLOCKED_TOOLTIP =
  'This product has stock batches (including fully consumed). Review them in the stock drawer — batch history is kept for traceability.'

interface ProductFormModalProps {
  opened: boolean
  onClose: () => void
  product?: Product | null
  onRequestDelete?: (product: Product) => void
  onViewStock?: (product: Product) => void
}

export default function ProductFormModal({
  opened,
  onClose,
  product,
  onRequestDelete,
  onViewStock,
}: ProductFormModalProps) {
  const queryClient = useQueryClient()
  const isEditing = !!product

  const form = useForm<ProductCreatePayload>({
    initialValues: {
      name: '',
      sku: '',
      unit_of_measure: 'UNIT',
      description: '',
    },
    validate: {
      name: isNotEmpty('Name is a required field'),
      sku: isNotEmpty('SKU is a required field'),
      unit_of_measure: isNotEmpty('Unit of measure is required'),
    },
  })

  useEffect(() => {
    if (product && opened) {
      form.setValues({
        name: product.name,
        sku: product.sku,
        unit_of_measure: product.unit_of_measure,
        description: product.description,
      })
    } else if (opened && !product) {
      form.reset()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [product, opened])

  const mutation = useMutation({
    mutationFn: (payload: ProductCreatePayload) =>
      isEditing ? updateProduct(product.id, payload) : createProduct(payload),
    onSuccess: () => {
      notifications.show({
        title: 'Success',
        message: `Product ${isEditing ? 'updated' : 'created'} successfully!`,
        color: 'green',
      })
      queryClient.invalidateQueries({ queryKey: ['products'] })
      onClose()
      form.reset()
    },
    onError: (error) => {
      const formErrors = getFormErrorsFromApi(getAxiosResponseData(error))
      if (formErrors) {
        form.setErrors(formErrors)
        notifications.show({
          title: 'Validation Error',
          message: 'Please check the form for errors.',
          color: 'red',
        })
      } else {
        notifications.show({
          title: 'Error',
          message: getApiErrorMessage(error),
          color: 'red',
        })
      }
    },
  })

  const handleSubmit = (values: ProductCreatePayload) => {
    mutation.mutate(values)
  }

  const deleteBlocked = isEditing && product.has_stock_batches

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={isEditing ? 'Edit Product' : 'Add Product'}
      size="md"
    >
      <form onSubmit={form.onSubmit(handleSubmit)}>
        <TextInput
          label="Name"
          placeholder="e.g. Kyoto Moss"
          withAsterisk
          {...form.getInputProps('name')}
        />

        <TextInput
          label="SKU"
          placeholder="e.g. MOSS-001"
          withAsterisk
          mt="md"
          {...form.getInputProps('sku')}
        />

        <Select
          label="Unit of Measure"
          withAsterisk
          mt="md"
          data={['UNIT', 'KG', 'G', 'L', 'ML']}
          {...form.getInputProps('unit_of_measure')}
        />

        <Textarea
          label="Description"
          placeholder="Optional product description"
          mt="md"
          minRows={3}
          {...form.getInputProps('description')}
        />

        {isEditing && deleteBlocked && (
          <Text size="sm" c="dimmed" mt="md">
            Stock batches block deletion even when on-hand quantity is zero.{' '}
            {onViewStock && (
              <Button
                variant="subtle"
                size="compact-sm"
                p={0}
                h="auto"
                onClick={() => {
                  onViewStock(product)
                  onClose()
                }}
              >
                View stock batches
              </Button>
            )}
          </Text>
        )}

        <Group justify="space-between" mt="xl" align="center">
          {isEditing ? (
            deleteBlocked ? (
              <Tooltip label={DELETE_BLOCKED_TOOLTIP} multiline maw={280}>
                <Box>
                  <Button color="red" variant="light" disabled>
                    Delete product
                  </Button>
                </Box>
              </Tooltip>
            ) : (
              <Button
                color="red"
                variant="light"
                onClick={() => onRequestDelete?.(product)}
              >
                Delete product
              </Button>
            )
          ) : (
            <span />
          )}
          <Group gap="sm">
            <Button variant="light" onClick={onClose} color="gray">
              Cancel
            </Button>
            <Button type="submit" color="green" loading={mutation.isPending}>
              {isEditing ? 'Save Changes' : 'Create Product'}
            </Button>
          </Group>
        </Group>
      </form>
    </Modal>
  )
}
