import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { activityApi } from '../../services/api'
import { Card, CardContent } from '../../components/ui/Card'
import {
  Activity,
  FileText,
  User,
  Image,
  Trash2,
  Edit2,
  Plus,
  LogIn,
  LogOut,
  Settings,
  Calendar,
  Filter,
  Search,
  Eye,
} from 'lucide-react'

function ActivityLogPage() {
  const [filters, setFilters] = useState({
    action: '',
    resource_type: '',
    user_id: '',
    date_from: '',
    date_to: '',
  })
  const [page, setPage] = useState(1)
  const perPage = 20

  // Fetch activity logs
  const { data: activityData, isLoading } = useQuery({
    queryKey: ['activity', filters, page],
    queryFn: () => activityApi.getAll({ ...filters, page, per_page: perPage }),
    select: (res) => res.data,
  })

  const activities = activityData?.items || activityData || []
  const totalPages = activityData?.total_pages || 1

  const getActionIcon = (action) => {
    const icons = {
      create: <Plus className="h-4 w-4 text-green-500" />,
      update: <Edit2 className="h-4 w-4 text-blue-500" />,
      delete: <Trash2 className="h-4 w-4 text-red-500" />,
      login: <LogIn className="h-4 w-4 text-purple-500" />,
      logout: <LogOut className="h-4 w-4 text-gray-500" />,
      view: <Eye className="h-4 w-4 text-gray-400" />,
    }
    return icons[action] || <Activity className="h-4 w-4 text-gray-400" />
  }

  const getResourceIcon = (resourceType) => {
    const icons = {
      content: <FileText className="h-4 w-4" />,
      user: <User className="h-4 w-4" />,
      media: <Image className="h-4 w-4" />,
      settings: <Settings className="h-4 w-4" />,
    }
    return icons[resourceType] || <Activity className="h-4 w-4" />
  }

  const getActionBadge = (action) => {
    const styles = {
      create: 'bg-green-100 text-green-700',
      update: 'bg-blue-100 text-blue-700',
      delete: 'bg-red-100 text-red-700',
      login: 'bg-purple-100 text-purple-700',
      logout: 'bg-gray-100 text-gray-700',
      view: 'bg-gray-100 text-gray-600',
    }
    return (
      <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${styles[action] || styles.view}`}>
        {action}
      </span>
    )
  }

  const formatDate = (dateString) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now - date
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins} min ago`
    if (diffHours < 24) return `${diffHours} hours ago`
    if (diffDays < 7) return `${diffDays} days ago`
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  const clearFilters = () => {
    setFilters({
      action: '',
      resource_type: '',
      user_id: '',
      date_from: '',
      date_to: '',
    })
    setPage(1)
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Activity Log</h1>
        <p className="text-gray-500 mt-1">Track all actions and changes in your CMS</p>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-2 mb-4">
            <Filter className="h-4 w-4 text-gray-400" />
            <span className="text-sm font-medium text-gray-700">Filters</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            <select
              value={filters.action}
              onChange={(e) => setFilters({ ...filters, action: e.target.value })}
              className="input"
            >
              <option value="">All Actions</option>
              <option value="create">Create</option>
              <option value="update">Update</option>
              <option value="delete">Delete</option>
              <option value="login">Login</option>
              <option value="logout">Logout</option>
            </select>

            <select
              value={filters.resource_type}
              onChange={(e) => setFilters({ ...filters, resource_type: e.target.value })}
              className="input"
            >
              <option value="">All Resources</option>
              <option value="content">Content</option>
              <option value="user">User</option>
              <option value="media">Media</option>
              <option value="category">Category</option>
              <option value="tag">Tag</option>
              <option value="comment">Comment</option>
            </select>

            <input
              type="date"
              value={filters.date_from}
              onChange={(e) => setFilters({ ...filters, date_from: e.target.value })}
              className="input"
              placeholder="From date"
            />

            <input
              type="date"
              value={filters.date_to}
              onChange={(e) => setFilters({ ...filters, date_to: e.target.value })}
              className="input"
              placeholder="To date"
            />

            <button
              onClick={clearFilters}
              className="text-sm text-gray-600 hover:text-gray-900"
            >
              Clear filters
            </button>
          </div>
        </CardContent>
      </Card>

      {/* Activity list */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
            </div>
          ) : activities.length === 0 ? (
            <div className="text-center py-12">
              <Activity className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900">No activity found</h3>
              <p className="text-gray-500 mt-1">Activity logs will appear here as actions are taken.</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-200">
              {activities.map((activity, index) => (
                <div key={activity.id || index} className="p-4 hover:bg-gray-50">
                  <div className="flex items-start gap-4">
                    {/* Action icon */}
                    <div className="flex-shrink-0 mt-1">
                      <div className="h-8 w-8 bg-gray-100 rounded-full flex items-center justify-center">
                        {getActionIcon(activity.action)}
                      </div>
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-medium text-gray-900">
                          {activity.user?.username || 'System'}
                        </span>
                        {getActionBadge(activity.action)}
                        <span className="text-gray-500">
                          {activity.resource_type}
                        </span>
                        {activity.resource_name && (
                          <span className="text-gray-700 font-medium truncate max-w-xs">
                            "{activity.resource_name}"
                          </span>
                        )}
                      </div>

                      {activity.description && (
                        <p className="text-sm text-gray-600 mt-1">{activity.description}</p>
                      )}

                      {/* Changes preview */}
                      {activity.changes && (
                        <div className="mt-2 text-xs bg-gray-50 rounded p-2 font-mono">
                          {typeof activity.changes === 'string'
                            ? activity.changes
                            : JSON.stringify(activity.changes, null, 2).substring(0, 200)}
                        </div>
                      )}

                      <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
                        <div className="flex items-center gap-1">
                          <Calendar className="h-3 w-3" />
                          <span>{formatDate(activity.created_at)}</span>
                        </div>
                        {activity.ip_address && (
                          <span>IP: {activity.ip_address}</span>
                        )}
                      </div>
                    </div>

                    {/* Resource icon */}
                    <div className="flex-shrink-0 text-gray-400">
                      {getResourceIcon(activity.resource_type)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-gray-500">
            Page {page} of {totalPages}
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage(Math.max(1, page - 1))}
              disabled={page === 1}
              className="px-3 py-1 text-sm border border-gray-300 rounded-lg disabled:opacity-50 hover:bg-gray-50"
            >
              Previous
            </button>
            <button
              onClick={() => setPage(Math.min(totalPages, page + 1))}
              disabled={page === totalPages}
              className="px-3 py-1 text-sm border border-gray-300 rounded-lg disabled:opacity-50 hover:bg-gray-50"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default ActivityLogPage
