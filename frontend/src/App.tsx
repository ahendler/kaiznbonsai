import { Navigate, Route, Routes } from 'react-router-dom'
import { Center, Loader } from '@mantine/core'
import type { ReactNode } from 'react'
import { useAuth } from '@/context/AuthContext'
import LoginPage from '@/pages/auth/LoginPage'
import RegisterPage from '@/pages/auth/RegisterPage'
import AppLayout from '@/components/layout/AppLayout'
import HomePage from '@/pages/home/HomePage'
import FinancialsPage from '@/pages/financials/FinancialsPage'
import ProductListPage from '@/pages/inventory/ProductListPage'
import PurchaseOrdersPage from '@/pages/orders/PurchaseOrdersPage'
import SalesOrdersPage from '@/pages/orders/SalesOrdersPage'
import HistoryPage from '@/pages/history/HistoryPage'

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
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<HomePage />} />
        <Route path="financials" element={<FinancialsPage />} />
        <Route path="history" element={<HistoryPage />} />
        <Route path="inventory/products" element={<ProductListPage />} />
        <Route path="orders">
          <Route index element={<Navigate to="/orders/purchases" replace />} />
          <Route path="purchases" element={<PurchaseOrdersPage />} />
          <Route path="sales" element={<SalesOrdersPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
