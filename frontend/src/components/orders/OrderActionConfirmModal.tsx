import { Badge, Button, Group, Modal, Stack, Text } from '@mantine/core'

interface OrderActionConfirmModalProps {
  opened: boolean
  orderId: number | null
  action: 'confirm' | 'cancel' | null
  title: string
  description: string
  loading: boolean
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
  onClose,
  onConfirm,
}: OrderActionConfirmModalProps) {
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
