import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'

// Layouts
import AuthLayout from './components/layouts/AuthLayout'
import DashboardLayout from './components/layouts/DashboardLayout'

// Auth Pages
import LoginPage from './pages/auth/LoginPage'
import RegisterPage from './pages/auth/RegisterPage'
import TwoFactorPage from './pages/auth/TwoFactorPage'

// Dashboard Pages
import DashboardPage from './pages/dashboard/DashboardPage'
import ContentListPage from './pages/content/ContentListPage'
import ContentEditPage from './pages/content/ContentEditPage'
import CategoriesPage from './pages/categories/CategoriesPage'
import TagsPage from './pages/tags/TagsPage'
import CommentsPage from './pages/comments/CommentsPage'
import UsersPage from './pages/users/UsersPage'
import TeamsPage from './pages/teams/TeamsPage'
import MediaPage from './pages/media/MediaPage'
import ApiKeysPage from './pages/apikeys/ApiKeysPage'
import WebhooksPage from './pages/webhooks/WebhooksPage'
import SettingsPage from './pages/settings/SettingsPage'
import ProfilePage from './pages/settings/ProfilePage'

// Error Pages
import NotFoundPage from './pages/errors/NotFoundPage'

// Protected Route Component
function ProtectedRoute({ children }) {
  const { isAuthenticated, isLoading } = useAuthStore()

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return children
}

// Public Route Component (redirect if authenticated)
function PublicRoute({ children }) {
  const { isAuthenticated, isLoading } = useAuthStore()

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />
  }

  return children
}

function App() {
  return (
    <Routes>
      {/* Auth Routes */}
      <Route element={<AuthLayout />}>
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
        <Route path="/2fa" element={<TwoFactorPage />} />
      </Route>

      {/* Dashboard Routes */}
      <Route
        element={
          <ProtectedRoute>
            <DashboardLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/content" element={<ContentListPage />} />
        <Route path="/content/new" element={<ContentEditPage />} />
        <Route path="/content/:id" element={<ContentEditPage />} />
        <Route path="/categories" element={<CategoriesPage />} />
        <Route path="/tags" element={<TagsPage />} />
        <Route path="/comments" element={<CommentsPage />} />
        <Route path="/users" element={<UsersPage />} />
        <Route path="/teams" element={<TeamsPage />} />
        <Route path="/media" element={<MediaPage />} />
        <Route path="/api-keys" element={<ApiKeysPage />} />
        <Route path="/webhooks" element={<WebhooksPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/profile" element={<ProfilePage />} />
      </Route>

      {/* Default Redirect */}
      <Route path="/" element={<Navigate to="/dashboard" replace />} />

      {/* 404 Page */}
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}

export default App
