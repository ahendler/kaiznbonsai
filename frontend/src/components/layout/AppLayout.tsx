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
  IconDashboard,
  IconReceipt,
} from '@tabler/icons-react'
import { useAuth } from '@/context/AuthContext'
import { authApi } from '@/api/auth'

const navItems = [
  { label: 'Dashboard', icon: IconDashboard, path: '/' },
  { label: 'Products', icon: IconBoxSeam, path: '/inventory/products' },
  { label: 'Orders', icon: IconReceipt, path: '/orders' },
]

function isNavItemActive(pathname: string, path: string): boolean {
  if (path === '/') {
    return pathname === '/'
  }
  return pathname.startsWith(path)
}

export default function AppLayout() {
  const [opened, { toggle, close }] = useDisclosure()
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
