import { Navigate, Route, Routes } from 'react-router-dom'
import { Center, Loader } from '@mantine/core'
import type { ReactNode } from 'react'
import { useAuth } from '@/context/AuthContext'
import LoginPage from '@/pages/auth/LoginPage'
import RegisterPage from '@/pages/auth/RegisterPage'

function ProtectedRoute({ children }: { children: ReactNode }) {
  const { state } = useAuth()
  if (state.isLoading) {
    return (
      <Center h="100vh">
        <Loader size="lg" />
      </Center>
    )
  }
  return state.isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />
}

function PublicRoute({ children }: { children: ReactNode }) {
  const { state } = useAuth()
  if (state.isLoading) {
    return (
      <Center h="100vh">
        <Loader size="lg" />
      </Center>
    )
  }
  return state.isAuthenticated ? <Navigate to="/" replace /> : <>{children}</>
}

export default function App() {
  return (
    <Routes>
      <Route
        path="/login"
        element={
          <PublicRoute>
            <LoginPage />
          </PublicRoute>
        }
      />
      <Route
        path="/register"
        element={
          <PublicRoute>
            <RegisterPage />
          </PublicRoute>
        }
      />
      {/* Placeholder — replaced with AppShell + dashboard in Phase 5 */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Center h="100vh">Authenticated ✓</Center>
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
