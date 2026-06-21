import { useEffect } from 'react'
import { Modal, TextInput, Select, Textarea, Button, Group } from '@mantine/core'
import { useForm, isNotEmpty } from '@mantine/form'
import { notifications } from '@mantine/notifications'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createProduct, updateProduct } from '@/api/inventory'
import type { Product, ProductCreatePayload } from '@/api/inventory'

interface ProductFormModalProps {
  opened: boolean
  onClose: () => void
  product?: Product | null
}

export default function ProductFormModal({ opened, onClose, product }: ProductFormModalProps) {
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

  // Pre-fill form when editing a product
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
    onError: (error: any) => {
      // If we have field-level errors (400 Bad Request from DRF)
      if (error.response?.data && typeof error.response.data === 'object') {
        const serverErrors = error.response.data
        const formErrors: Record<string, string> = {}

        // Map array of error strings to a single string for Mantine form
        Object.keys(serverErrors).forEach((key) => {
          if (Array.isArray(serverErrors[key])) {
            formErrors[key] = serverErrors[key][0]
          } else {
            formErrors[key] = serverErrors[key]
          }
        })
        form.setErrors(formErrors)

        notifications.show({
          title: 'Validation Error',
          message: 'Please check the form for errors.',
          color: 'red',
        })
      } else {
        notifications.show({
          title: 'Error',
          message: error.message || 'An unexpected error occurred.',
          color: 'red',
        })
      }
    },
  })

  const handleSubmit = (values: ProductCreatePayload) => {
    mutation.mutate(values)
  }

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

        <Group justify="flex-end" mt="xl">
          <Button variant="light" onClick={onClose} color="gray">
            Cancel
          </Button>
          <Button type="submit" color="green" loading={mutation.isPending}>
            {isEditing ? 'Save Changes' : 'Create Product'}
          </Button>
        </Group>
      </form>
    </Modal>
  )
}
