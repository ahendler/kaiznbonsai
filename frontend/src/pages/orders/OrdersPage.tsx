import { Container, Title, Tabs } from '@mantine/core';
import { IconTruckDelivery, IconCash } from '@tabler/icons-react';
import { PurchaseOrderTable } from '../../components/orders/PurchaseOrderTable';

export default function OrdersPage() {
  return (
    <Container size="xl">
      <Title order={2} mb="xl">
        Orders
      </Title>

      <Tabs defaultValue="purchases">
        <Tabs.List mb="md">
          <Tabs.Tab value="purchases" leftSection={<IconTruckDelivery size={16} />}>
            Purchase Orders
          </Tabs.Tab>
          <Tabs.Tab value="sales" leftSection={<IconCash size={16} />}>
            Sales Orders
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="purchases" pt="md">
          <PurchaseOrderTable />
        </Tabs.Panel>

        <Tabs.Panel value="sales">
          {/* SalesOrderTable goes here later */}
          <p>Sales Orders list goes here.</p>
        </Tabs.Panel>
      </Tabs>
    </Container>
  );
}
