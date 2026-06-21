import {
  AppShell,
  Burger,
  Group,
  NavLink,
  Button,
  Drawer,
  Text,
  ActionIcon,
  Menu,
  Avatar,
  Box,
  Stack,
  Affix,
} from '@mantine/core'
import { useDisclosure } from '@mantine/hooks'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import {
  IconBoxSeam,
  IconHistory,
  IconSettings,
  IconMessageChatbot,
  IconLogout,
  IconUser,
  IconBell,
  IconReceipt,
} from '@tabler/icons-react'
import { useAuth } from '@/context/AuthContext'

export default function AppLayout() {
  const [opened, { toggle, close }] = useDisclosure()
  const [jptOpened, { open: openJpt, close: closeJpt }] = useDisclosure(false)
  const navigate = useNavigate()
  const location = useLocation()
  const { actions } = useAuth()

  const navItems = [
    { label: 'Products', icon: IconBoxSeam, path: '/inventory/products' },
    { label: 'Orders', icon: IconReceipt, path: '/orders' },
    { label: 'History', icon: IconHistory, path: '/history' },
    { label: 'Settings', icon: IconSettings, path: '/settings' },
  ]

  return (
    <>
      <AppShell
        header={{ height: 60 }}
        aside={{ width: 300, breakpoint: 'sm', collapsed: { desktop: !jptOpened, mobile: !jptOpened } }}
        padding="md"
      >
        <AppShell.Header>
          <Group h="100%" px="md" justify="space-between">
            <Group gap="md">
              <Burger opened={opened} onClick={toggle} size="md" />
              <img
                src="/logo.png"
                alt="KaiznBonsai Logo"
                style={{ height: 32, cursor: 'pointer' }}
                onClick={() => navigate('/')}
              />
            </Group>

            <Group gap="md">
              <ActionIcon variant="subtle" color="gray" size="xl" radius="xl">
                <IconBell size={24} stroke={1.5} />
              </ActionIcon>
              
              <Menu shadow="md" width={200} position="bottom-end">
                <Menu.Target>
                  <ActionIcon variant="transparent" size="xl" radius="xl">
                    <Avatar radius="xl" size="md" color="green" />
                  </ActionIcon>
                </Menu.Target>

                <Menu.Dropdown>
                  <Menu.Label>Application</Menu.Label>
                  <Menu.Item leftSection={<IconUser size={14} />}>Profile</Menu.Item>
                  <Menu.Divider />
                  <Menu.Item
                    color="red"
                    leftSection={<IconLogout size={14} />}
                    onClick={() => actions.logout()}
                  >
                    Logout
                  </Menu.Item>
                </Menu.Dropdown>
              </Menu>
            </Group>
          </Group>
        </AppShell.Header>

        <AppShell.Main>
          <Outlet />
        </AppShell.Main>

        <AppShell.Aside p="md">
          <Box ta="center" mt="xl">
            <IconMessageChatbot size={64} color="var(--mantine-color-gray-4)" />
            <Text c="dimmed" mt="md" size="sm" fw={500}>
              JPT Assistant
            </Text>
            <Text c="dimmed" mt="xs" size="sm">
              AI Assistant integration coming in Phase 12.
            </Text>
          </Box>
        </AppShell.Aside>
      </AppShell>

      {/* Navigation Drawer */}
      <Drawer
        opened={opened}
        onClose={close}
        title={<img src="/logo-letter.png" alt="KaiznBonsai" style={{ height: 24, display: 'block' }} />}
        position="left"
        padding="md"
        size="sm"
        zIndex={1000}
      >
        <style>{`
          .nav-item-hover {
            transition: transform 0.2s ease, background-color 0.2s ease;
          }
          .nav-item-hover:hover {
            transform: translateX(6px);
          }
        `}</style>
        <Stack gap="sm" mt="md">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              className="nav-item-hover"
              label={<Text size="lg" fw={500}>{item.label}</Text>}
              leftSection={<item.icon size={24} stroke={1.5} />}
              active={location.pathname.startsWith(item.path)}
              onClick={() => {
                navigate(item.path)
                close()
              }}
              variant="light"
              color="green"
              style={{ borderRadius: 8, padding: '12px 16px' }}
            />
          ))}
        </Stack>
      </Drawer>

      {/* JPT Floating Trigger */}
      <Affix position={{ bottom: 20, right: 20 }} zIndex={900}>
        <Button
          onClick={jptOpened ? closeJpt : openJpt}
          style={{ boxShadow: '0 4px 12px rgba(0,0,0,0.15)' }}
          color="dark"
          size="lg"
          radius="xl"
        >
          {jptOpened ? 'Close JPT' : 'Ask JPT'}
        </Button>
      </Affix>
    </>
  )
}
