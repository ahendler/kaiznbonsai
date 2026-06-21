import { Drawer, Button, Group, Select, NumberInput, TextInput, Stack, ActionIcon, Divider, Box, Text } from '@mantine/core';
import { useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import { IconTrash, IconPlus } from '@tabler/icons-react';
import { useQuery } from '@tanstack/react-query';
import { listProducts } from '../../api/inventory';
import { useCreatePurchaseOrder } from '../../api/orders';

interface Props {
  opened: boolean;
  onClose: () => void;
}

export function PurchaseOrderDrawer({ opened, onClose }: Props) {
  const { data: productsData } = useQuery({
    queryKey: ['products'],
    queryFn: () => listProducts(null)
  });
  const products = productsData?.results || [];
  const createMutation = useCreatePurchaseOrder();

  const form = useForm({
    initialValues: {
      title: '',
      items: [
        { product_id: null as string | null, quantity: 1, unit_cost: 0, lot_code: '', best_before: '' }
      ]
    },
    validate: {
      items: {
        product_id: (value) => (!value ? 'Required' : null),
        quantity: (value) => (value <= 0 ? 'Must be greater than 0' : null),
        unit_cost: (value) => (value < 0 ? 'Cannot be negative' : null),
      }
    }
  });

  const productOptions = products?.map(p => ({
    value: p.id.toString(),
    label: `${p.name} (${p.sku}) [${p.unit_of_measure}]`
  })) || [];

  const handleSubmit = form.onSubmit((values) => {
    // format date
    const formattedItems = values.items.map(item => ({
      product_id: Number(item.product_id),
      quantity: item.quantity,
      unit_cost: item.unit_cost,
      lot_code: item.lot_code || undefined,
      best_before: item.best_before ? item.best_before : null
    }));

    createMutation.mutate({ title: values.title || undefined, items_data: formattedItems }, {
      onSuccess: () => {
        notifications.show({ title: 'Success', message: "Purchase Order drafted successfully!", color: 'green' });
        form.reset();
        onClose();
      },
      onError: (error: any) => {
        notifications.show({ title: 'Error', message: "Failed to create order: " + (error.response?.data?.[0] || error.message), color: 'red' });
      }
    });
  });

  return (
    <Drawer opened={opened} onClose={onClose} title="Create Purchase Order" position="right" size="xl">
      <form onSubmit={handleSubmit}>
        <Stack gap="md">
          <TextInput
            label="Order Title (Optional)"
            placeholder="e.g. Q3 Restock"
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
                  label="Quantity"
                  withAsterisk
                  min={0.001}
                  decimalScale={3}
                  {...form.getInputProps(`items.${index}.quantity`)}
                />
                <NumberInput
                  label="Unit Cost ($)"
                  withAsterisk
                  min={0}
                  decimalScale={2}
                  {...form.getInputProps(`items.${index}.unit_cost`)}
                />
              </Group>
              <Group grow mt="sm">
                <TextInput
                  label="Lot Code (Optional)"
                  placeholder="Auto-generated on confirm"
                  {...form.getInputProps(`items.${index}.lot_code`)}
                />
                <TextInput
                  type="date"
                  label="Best Before (Optional)"
                  {...form.getInputProps(`items.${index}.best_before`)}
                />
              </Group>
            </Box>
          ))}

          <Button variant="light" leftSection={<IconPlus size={16} />} onClick={() => form.insertListItem('items', { product_id: null, quantity: 1, unit_cost: 0, lot_code: '', best_before: '' })}>
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
