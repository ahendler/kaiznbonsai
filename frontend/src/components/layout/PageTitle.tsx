import { Group, Text, Title, type TitleProps } from '@mantine/core'

interface PageTitleProps {
  title: string
  subtitle?: string
  order?: TitleProps['order']
  mb?: string | number
}

export function PageTitle({ title, subtitle, order = 2, mb }: PageTitleProps) {
  return (
    <Group gap="sm" align="baseline" mb={mb} wrap="wrap">
      <Title order={order}>{title}</Title>
      {subtitle ? (
        <Text c="dimmed" size="sm">
          {subtitle}
        </Text>
      ) : null}
    </Group>
  )
}
