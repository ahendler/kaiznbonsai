import { Badge, Button, Group, Modal, SegmentedControl, Stack, Text } from '@mantine/core'
import type { StockAllocationStrategy } from '@/api/orders'
import { ALLOCATION_OPTIONS, getAllocationDescription } from '@/utils/orders'

interface OrderActionConfirmModalProps {
  opened: boolean
  orderId: number | null
  action: 'confirm' | 'cancel' | null
  title: string
  description: string
  loading: boolean
  showAllocationToggle?: boolean
  allocationStrategy?: StockAllocationStrategy
  onAllocationStrategyChange?: (strategy: StockAllocationStrategy) => void
  onClose: () => void
  onConfirm: (orderId: number) => void
}

export function OrderActionConfirmModal({
  opened,
  orderId,
  action,
  title,
  description,
  loading,
  showAllocationToggle = false,
  allocationStrategy = 'FIFO',
  onAllocationStrategyChange,
  onClose,
  onConfirm,
}: OrderActionConfirmModalProps) {
  const allocationDescription = getAllocationDescription(allocationStrategy)

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={
        <Badge color={action === 'confirm' ? 'green' : 'red'} variant="light" size="lg" radius="sm">
          {title}
        </Badge>
      }
      centered
    >
      <Stack gap="xs" mb="lg">
        <Text size="sm">Are you sure you want to {action} Order #{orderId}?</Text>
        <Text size="sm" c="dimmed">{description}</Text>
        {showAllocationToggle && action === 'confirm' && (
          <Stack gap={6} mt="sm">
            <Text size="sm" fw={500}>How should stock be deducted?</Text>
            <SegmentedControl
              value={allocationStrategy}
              onChange={(value) => onAllocationStrategyChange?.(value as StockAllocationStrategy)}
              data={ALLOCATION_OPTIONS.map((option) => ({
                label: option.label,
                value: option.value,
              }))}
              fullWidth
            />
            {allocationDescription && (
              <Text size="sm" c="dimmed">{allocationDescription}</Text>
            )}
          </Stack>
        )}
      </Stack>
      <Group justify="flex-end">
        <Button variant="default" onClick={onClose}>Go Back</Button>
        <Button
          color={action === 'confirm' ? 'green' : 'red'}
          loading={loading}
          onClick={() => {
            if (orderId != null) onConfirm(orderId)
            onClose()
          }}
        >
          Yes, {action}
        </Button>
      </Group>
    </Modal>
  )
}
