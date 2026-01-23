import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { contentApi } from '../../services/api'
import Button from '../../components/ui/Button'
import { Card, CardContent } from '../../components/ui/Card'
import { useToast } from '../../components/ui/Toast'
import { SkeletonTable } from '../../components/ui/Skeleton'
import {
  Plus,
  Search,
  Edit,
  Trash2,
  CheckCircle,
  Clock,
  XCircle,
  FileText,
  AlertCircle,
  RefreshCw,
} from 'lucide-react'

const statusColors = {
  published: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  draft: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  archived: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
}

const statusIcons = {
  published: CheckCircle,
  draft: Clock,
  archived: XCircle,
}

function ContentListPage() {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const queryClient = useQueryClient()
  const { toast } = useToast()

  const { data: contentList, isLoading, error, refetch } = useQuery({
    queryKey: ['content', search, statusFilter],
    queryFn: () => contentApi.getAll({ search, status: statusFilter || undefined }),
    select: (res) => res.data,
  })

  const deleteMutation = useMutation({
    mutationFn: (id) => contentApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries(['content'])
      toast({
        title: 'Content deleted',
        description: 'The content has been deleted successfully.',
        variant: 'success',
      })
    },
    onError: (error) => {
      toast({
        title: 'Failed to delete',
        description: error.response?.data?.detail || error.message || 'An error occurred while deleting the content.',
        variant: 'error',
      })
    },
  })

  const handleDelete = (id, title) => {
    if (window.confirm(`Are you sure you want to delete "${title}"?`)) {
      deleteMutation.mutate(id)
    }
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Content</h1>
            <p className="text-gray-500 dark:text-gray-400 mt-1">Manage your articles, posts, and pages</p>
          </div>
        </div>
        <div className="flex flex-col items-center justify-center py-16 space-y-4">
          <AlertCircle className="h-12 w-12 text-red-500" />
          <div className="text-center">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Failed to load content</h2>
            <p className="text-gray-600 dark:text-gray-400 mt-1">
              {error.response?.data?.detail || error.message || 'An error occurred while loading content.'}
            </p>
          </div>
          <button
            onClick={() => refetch()}
            className="btn btn-secondary flex items-center gap-2"
          >
            <RefreshCw className="h-4 w-4" />
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Content</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">Manage your articles, posts, and pages</p>
        </div>
        <Link to="/content/new">
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            New Content
          </Button>
        </Link>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search content..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="input pl-10 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              />
            </div>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="input w-full sm:w-40 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
            >
              <option value="">All Status</option>
              <option value="published">Published</option>
              <option value="draft">Draft</option>
              <option value="archived">Archived</option>
            </select>
          </div>
        </CardContent>
      </Card>

      {/* Content list */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <SkeletonTable rows={5} columns={5} />
          ) : contentList && contentList.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
                    <th className="text-left py-3 px-6 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Title
                    </th>
                    <th className="text-left py-3 px-6 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="text-left py-3 px-6 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Author
                    </th>
                    <th className="text-left py-3 px-6 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Updated
                    </th>
                    <th className="text-right py-3 px-6 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                  {contentList.map((item) => {
                    const StatusIcon = statusIcons[item.status] || Clock
                    return (
                      <tr key={item.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                        <td className="py-4 px-6">
                          <div>
                            <Link
                              to={`/content/${item.id}`}
                              className="font-medium text-gray-900 dark:text-white hover:text-primary-600 dark:hover:text-primary-400"
                            >
                              {item.title}
                            </Link>
                            {item.excerpt && (
                              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 line-clamp-1">
                                {item.excerpt}
                              </p>
                            )}
                          </div>
                        </td>
                        <td className="py-4 px-6">
                          <span
                            className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${
                              statusColors[item.status] || 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                            }`}
                          >
                            <StatusIcon className="h-3 w-3" />
                            {item.status.charAt(0).toUpperCase() + item.status.slice(1)}
                          </span>
                        </td>
                        <td className="py-4 px-6 text-sm text-gray-500 dark:text-gray-400">
                          {item.author?.username || 'Unknown'}
                        </td>
                        <td className="py-4 px-6 text-sm text-gray-500 dark:text-gray-400">
                          {new Date(item.updated_at).toLocaleDateString()}
                        </td>
                        <td className="py-4 px-6 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Link
                              to={`/content/${item.id}`}
                              className="p-2 text-gray-400 hover:text-primary-600 dark:hover:text-primary-400 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
                            >
                              <Edit className="h-4 w-4" />
                            </Link>
                            <button
                              onClick={() => handleDelete(item.id, item.title)}
                              disabled={deleteMutation.isPending}
                              className="p-2 text-gray-400 hover:text-red-600 dark:hover:text-red-400 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-12">
              <FileText className="h-12 w-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-1">No content found</h3>
              <p className="text-gray-500 dark:text-gray-400 mb-4">Get started by creating your first piece of content</p>
              <Link to="/content/new">
                <Button>
                  <Plus className="h-4 w-4 mr-2" />
                  Create Content
                </Button>
              </Link>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default ContentListPage
