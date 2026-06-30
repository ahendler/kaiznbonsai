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
} from '@mantine/core'
import { useForm } from '@mantine/form'
import { notifications } from '@mantine/notifications'
import { authApi } from '@/api/auth'
import { applyApiFieldErrors, getApiErrorMessage } from '@/api/errors'

interface RegisterFormValues {
  email: string
  password: string
  password_confirm: string
}

export default function RegisterPage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)

  const form = useForm<RegisterFormValues>({
    initialValues: { email: '', password: '', password_confirm: '' },
    validate: {
      email: (v) => (/^\S+@\S+$/.test(v) ? null : 'Enter a valid email'),
      password: (v) => (v.length >= 8 ? null : 'Password must be at least 8 characters'),
      password_confirm: (v, values) =>
        v === values.password ? null : 'Passwords do not match',
    },
  })

  const handleSubmit = async (values: RegisterFormValues) => {
    setLoading(true)
    try {
      await authApi.register(values)
      notifications.show({
        title: 'Account created',
        message: 'You can now sign in.',
        color: 'green',
      })
      navigate('/login', { replace: true })
    } catch (err: unknown) {
      if (!applyApiFieldErrors(form, err)) {
        notifications.show({
          title: 'Registration failed',
          message: getApiErrorMessage(err, 'Something went wrong. Please try again.'),
          color: 'red',
        })
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <Container size={440} my={80}>
      <Title ta="center" mb="md">Create an account</Title>

      <Paper withBorder shadow="md" p="xl" radius="md">
        <form onSubmit={form.onSubmit(handleSubmit)}>
          <Stack gap="sm">
            <TextInput
              label="Email"
              placeholder="you@example.com"
              required
              {...form.getInputProps('email')}
            />

            <PasswordInput
              label="Password"
              placeholder="At least 8 characters"
              required
              {...form.getInputProps('password')}
            />

            <PasswordInput
              label="Confirm password"
              placeholder="Repeat your password"
              required
              {...form.getInputProps('password_confirm')}
            />

            <Button type="submit" fullWidth loading={loading} mt="sm">
              Create account
            </Button>
          </Stack>
        </form>

        <Text ta="center" mt="md" size="sm">
          Already have an account?{' '}
          <Text component={Link} to="/login" c="blue" td="underline">
            Sign in
          </Text>
        </Text>
      </Paper>
    </Container>
  )
}
