import { Center, Stack, Text } from '@mantine/core'

export default function DashboardPage() {
  return (
    <Center h="100%">
      <Stack align="center" gap="md" mt="xl">
        <img src="/logo.png" alt="KaiznBonsai" style={{ width: 120, opacity: 0.1 }} />
        <Text c="dimmed" size="lg" fw={500}>
          Welcome to KaiznBonsai
        </Text>
        <Text c="dimmed" size="sm">
          Dashboard widgets coming in a future phase.
        </Text>
      </Stack>
    </Center>
  )
}
