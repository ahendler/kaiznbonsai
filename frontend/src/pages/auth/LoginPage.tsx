import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  TextInput,
  PasswordInput,
  Button,
  Paper,
  Title,
  Text,
  Container,
  Stack,
  Alert,
  Image,
  Center,
} from '@mantine/core'
import { useForm } from '@mantine/form'
import { notifications } from '@mantine/notifications'
import { authApi } from '@/api/auth'
import { useAuth } from '@/context/AuthContext'

interface LoginFormValues {
  email: string
  password: string
}

export default function LoginPage() {
  const { dispatch } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const form = useForm<LoginFormValues>({
    initialValues: { email: '', password: '' },
    validate: {
      email: (v) => (/^\S+@\S+$/.test(v) ? null : 'Enter a valid email'),
      password: (v) => (v.length > 0 ? null : 'Password is required'),
    },
  })

  const handleSubmit = async (values: LoginFormValues) => {
    setLoading(true)
    setError(null)
    try {
      const data = await authApi.login(values)
      dispatch({ type: 'SET_AUTH', payload: { token: data.access, user: data.user } })
      navigate('/', { replace: true })
    } catch {
      setError('Invalid email or password.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Container size={440} my={80}>
      <Center mb="xl">
        <Image src="/logo-letter.png" alt="KaiznBonsai" h={50} w="auto" fit="contain" />
      </Center>

      <Paper withBorder shadow="md" p="xl" radius="md">
        <form onSubmit={form.onSubmit(handleSubmit)}>
          <Stack gap="sm">
            {error && <Alert color="red">{error}</Alert>}

            <TextInput
              label="Email"
              placeholder="you@example.com"
              required
              {...form.getInputProps('email')}
            />

            <PasswordInput
              label="Password"
              placeholder="Your password"
              required
              {...form.getInputProps('password')}
            />

            <Button type="submit" fullWidth loading={loading} mt="sm">
              Sign in
            </Button>
          </Stack>
        </form>

        <Text ta="center" mt="md" size="sm">
          No account?{' '}
          <Text component={Link} to="/register" c="blue" td="underline">
            Register
          </Text>
        </Text>
      </Paper>
    </Container>
  )
}
