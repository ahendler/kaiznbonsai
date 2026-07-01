import { useState } from 'react'
import {
  AppShell,
  Burger,
  Group,
  NavLink,
  Drawer,
  Text,
  ActionIcon,
  Menu,
  Avatar,
  Stack,
} from '@mantine/core'
import { useDisclosure } from '@mantine/hooks'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import {
  IconBoxSeam,
  IconLogout,
  IconHome,
  IconChartBar,
  IconTruckDelivery,
  IconCash,
  IconHistory,
} from '@tabler/icons-react'
import { useAuth } from '@/context/AuthContext'
import { authApi } from '@/api/auth'
import type { ChatMessage } from '@/api/assistant'
import AssistantFab from '@/components/assistant/AssistantFab'

const navItems = [
  { label: 'Home', icon: IconHome, path: '/' },
  { label: 'Financials', icon: IconChartBar, path: '/financials' },
  { label: 'Products', icon: IconBoxSeam, path: '/inventory/products' },
  { label: 'Purchases', icon: IconTruckDelivery, path: '/orders/purchases' },
  { label: 'Sales', icon: IconCash, path: '/orders/sales' },
  { label: 'Stock History', icon: IconHistory, path: '/history' },
]

function isNavItemActive(pathname: string, path: string): boolean {
  if (path === '/') {
    return pathname === '/'
  }
  return pathname === path || pathname.startsWith(`${path}/`)
}

function showAssistant(pathname: string): boolean {
  return pathname === '/' || pathname.startsWith('/financials')
}

export default function AppLayout() {
  const [opened, { toggle, close }] = useDisclosure()
  const [chatOpened, { open: openChat, close: closeChat }] = useDisclosure(false)
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([])
  const navigate = useNavigate()
  const location = useLocation()
  const { dispatch } = useAuth()

  return (
    <>
      <AppShell header={{ height: 60 }} padding="md">
        <AppShell.Header>
          <Group h="100%" px="md" justify="space-between">
            <Group gap="md">
              <Burger opened={opened} onClick={toggle} size="md" />
              <img
                src="/logo.png"
                alt="KaiznBonsai Logo"
                className="h-8 cursor-pointer"
                onClick={() => navigate('/')}
              />
            </Group>

            <Menu shadow="md" width={200} position="bottom-end">
              <Menu.Target>
                <ActionIcon variant="transparent" size="xl" radius="xl">
                  <Avatar radius="xl" size="md" color="green" />
                </ActionIcon>
              </Menu.Target>

              <Menu.Dropdown>
                <Menu.Label>Application</Menu.Label>
                <Menu.Item
                  color="red"
                  leftSection={<IconLogout size={14} />}
                  onClick={async () => {
                    await authApi.logout()
                    dispatch({ type: 'CLEAR_AUTH' })
                  }}
                >
                  Logout
                </Menu.Item>
              </Menu.Dropdown>
            </Menu>
          </Group>
        </AppShell.Header>

        <AppShell.Main>
          <Outlet />
        </AppShell.Main>
      </AppShell>

      {showAssistant(location.pathname) && (
        <AssistantFab
          opened={chatOpened}
          onOpen={openChat}
          onClose={closeChat}
          messages={chatMessages}
          setMessages={setChatMessages}
        />
      )}

      <Drawer
        opened={opened}
        onClose={close}
        title={
          <img
            src="/logo-letter.png"
            alt="KaiznBonsai"
            className="block h-6"
          />
        }
        position="left"
        padding="md"
        size="sm"
        zIndex={1000}
      >
        <Stack gap="sm" mt="md">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              className="rounded-lg px-4 py-3 transition-transform duration-200 ease-in-out hover:translate-x-1.5"
              label={<Text size="lg" fw={500}>{item.label}</Text>}
              leftSection={<item.icon size={24} stroke={1.5} />}
              active={isNavItemActive(location.pathname, item.path)}
              onClick={() => {
                navigate(item.path)
                close()
              }}
              variant="light"
              color="green"
            />
          ))}
        </Stack>
      </Drawer>
    </>
  )
}
