import { ActionIcon, Code, Group, Popover, Stack, Text } from '@mantine/core'
import { IconInfoCircle } from '@tabler/icons-react'

interface MetricColumnHeaderProps {
  label: string
  formula: string
  description?: string
}

export default function MetricColumnHeader({ label, formula, description }: MetricColumnHeaderProps) {
  return (
    <Group gap={4} wrap="nowrap" component="span" className="inline-flex">
      <Text span inherit fw={600}>
        {label}
      </Text>
      <Popover position="top" withArrow shadow="md" width={280} trapFocus={false}>
        <Popover.Target>
          <ActionIcon
            variant="subtle"
            color="gray"
            size="xs"
            aria-label={`About ${label}`}
            className="shrink-0"
          >
            <IconInfoCircle size={14} stroke={1.75} />
          </ActionIcon>
        </Popover.Target>
        <Popover.Dropdown>
          <Stack gap={6}>
            <Text size="sm" fw={600} lh={1.3}>
              {label}
            </Text>
            <Code block fz="xs" className="whitespace-normal">
              {formula}
            </Code>
            {description && (
              <Text size="xs" c="dimmed" lh={1.4}>
                {description}
              </Text>
            )}
          </Stack>
        </Popover.Dropdown>
      </Popover>
    </Group>
  )
}
