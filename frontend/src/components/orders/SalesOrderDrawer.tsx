import { Drawer, Button, Group, Select, NumberInput, TextInput, Stack, ActionIcon, Divider, Box, Text } from '@mantine/core';
import { useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import { IconTrash, IconPlus } from '@tabler/icons-react';
import { useQuery } from '@tanstack/react-query';
import { listProducts } from '../../api/inventory';
import { useCreateSalesOrder } from '../../api/orders';

interface Props {
  opened: boolean;
  onClose: () => void;
}

export function SalesOrderDrawer({ opened, onClose }: Props) {
  const { data: productsData } = useQuery({
    queryKey: ['products'],
    queryFn: () => listProducts(null)
  });
  const products = productsData?.results || [];
  const createMutation = useCreateSalesOrder();

  const form = useForm({
    initialValues: {
      title: '',
      items: [
        { product_id: null as string | null, quantity: 1, unit_price: 0 }
      ]
    },
    validate: {
      items: {
        product_id: (value) => (!value ? 'Required' : null),
        quantity: (value, values, path) => {
          if (value <= 0) return 'Must be greater than 0';
          
          // Optional: check if quantity exceeds available stock
          const match = path.match(/items\.(\d+)\.quantity/);
          if (match) {
            const index = parseInt(match[1], 10);
            const productId = values.items[index]?.product_id;
            if (productId) {
              const product = products.find((p: any) => p.id.toString() === productId);
              if (product && parseFloat(product.total_stock) < value) {
                return `Insufficient stock (Available: ${product.total_stock})`;
              }
            }
          }
          return null;
        },
        unit_price: (value) => (value < 0 ? 'Cannot be negative' : null),
      }
    }
  });

  const productOptions = products?.map((p: any) => ({
    value: p.id.toString(),
    label: `${p.name} (${p.sku}) [${p.unit_of_measure}] - Avail: ${parseFloat(p.total_stock)}`
  })) || [];

  const handleSubmit = form.onSubmit((values) => {
    const formattedItems = values.items.map(item => ({
      product_id: Number(item.product_id),
      quantity: item.quantity,
      unit_price: item.unit_price,
    }));

    createMutation.mutate({ title: values.title || undefined, items_data: formattedItems }, {
      onSuccess: () => {
        notifications.show({ title: 'Success', message: "Sales Order drafted successfully!", color: 'green' });
        form.reset();
        onClose();
      },
      onError: (error: any) => {
        notifications.show({ title: 'Error', message: "Failed to create order: " + (error.response?.data?.[0] || error.message), color: 'red' });
      }
    });
  });

  return (
    <Drawer opened={opened} onClose={onClose} title="Create Sales Order" position="right" size="xl">
      <form onSubmit={handleSubmit}>
        <Stack gap="md">
          <TextInput
            label="Order Title (Optional)"
            placeholder="e.g. Q4 Wholesale"
            {...form.getInputProps('title')}
          />
          <Text fw={500} size="sm">Line Items</Text>
          {form.values.items.map((_item, index) => (
            <Box key={index} p="sm" style={{ border: '1px solid #eee', borderRadius: 8 }}>
              <Group align="flex-end" mb="sm">
                <Select
                  label="Product"
                  placeholder="Select product"
                  data={productOptions}
                  searchable
                  style={{ flex: 1 }}
                  withAsterisk
                  {...form.getInputProps(`items.${index}.product_id`)}
                />
                <ActionIcon color="red" onClick={() => form.removeListItem('items', index)} disabled={form.values.items.length === 1}>
                  <IconTrash size={16} />
                </ActionIcon>
              </Group>
              <Group grow>
                <NumberInput
                  label="Quantity to Deduct"
                  withAsterisk
                  min={0.001}
                  decimalScale={3}
                  {...form.getInputProps(`items.${index}.quantity`)}
                />
                <NumberInput
                  label="Unit Price ($)"
                  withAsterisk
                  min={0}
                  decimalScale={2}
                  {...form.getInputProps(`items.${index}.unit_price`)}
                />
              </Group>
            </Box>
          ))}

          <Button variant="light" leftSection={<IconPlus size={16} />} onClick={() => form.insertListItem('items', { product_id: null, quantity: 1, unit_price: 0 })}>
            Add Line Item
          </Button>

          <Divider my="md" />
          
          <Group justify="flex-end">
            <Button variant="default" onClick={onClose}>Cancel</Button>
            <Button type="submit" loading={createMutation.isPending}>Save Draft</Button>
          </Group>
        </Stack>
      </form>
    </Drawer>
  );
}
