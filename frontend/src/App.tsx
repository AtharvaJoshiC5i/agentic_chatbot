import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { ProtectedRoute } from './components/ProtectedRoute'
import { AuthProvider, useAuth } from './context/AuthContext'
import { LlmProvider } from './context/LlmContext'
import { ChatAppPage } from './pages/ChatAppPage'
import { DataBrowserPage } from './pages/DataBrowserPage'
import { DashboardPage } from './pages/DashboardPage'
import { MonitoringPage } from './pages/MonitoringPage'
import { LoginPage } from './pages/LoginPage'
import { TasksPage } from './pages/TasksPage'
import { ToastProvider } from './context/ToastContext'
import { usesPersonaDashboardHome } from './lib/personaWorkspace'

function HomeRedirect() {
  const { isAuthenticated, role } = useAuth()
  if (!isAuthenticated) return <Navigate to="/login" replace />
  const home = usesPersonaDashboardHome(role) ? '/workspace/dashboard' : '/workspace'
  return <Navigate to={home} replace />
}

function WorkspaceRoute() {
  const { username } = useAuth()
  if (!username?.trim()) {
    return (
      <div className="workspace-shell flex h-dvh items-center justify-center text-sm text-stone-500">
        Preparing your workspace…
      </div>
    )
  }
  return (
    <LlmProvider>
      <ChatAppPage key={username} />
    </LlmProvider>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
        <Routes>
          <Route path="/" element={<HomeRedirect />} />
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/workspace"
            element={
              <ProtectedRoute>
                <WorkspaceRoute />
              </ProtectedRoute>
            }
          />
          <Route
            path="/workspace/data"
            element={
              <ProtectedRoute>
                <DataBrowserPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/workspace/dashboard"
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/workspace/monitoring"
            element={
              <ProtectedRoute>
                <MonitoringPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/workspace/approvals"
            element={
              <ProtectedRoute>
                <Navigate to="/workspace/dashboard" replace />
              </ProtectedRoute>
            }
          />
          <Route
            path="/workspace/tasks"
            element={
              <ProtectedRoute>
                <TasksPage />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<HomeRedirect />} />
        </Routes>
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}
