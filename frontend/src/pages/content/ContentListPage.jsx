import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { contentApi } from '../../services/api'
import Button from '../../components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card'
import {
  Plus,
  Search,
  Edit,
  Trash2,
  Eye,
  MoreVertical,
  CheckCircle,
  Clock,
  XCircle,
} from 'lucide-react'

const statusColors = {
  published: 'bg-green-100 text-green-700',
  draft: 'bg-yellow-100 text-yellow-700',
  archived: 'bg-gray-100 text-gray-700',
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

  const { data: contentList, isLoading } = useQuery({
    queryKey: ['content', search, statusFilter],
    queryFn: () => contentApi.getAll({ search, status: statusFilter || undefined }),
    select: (res) => res.data,
  })

  const deleteMutation = useMutation({
    mutationFn: (id) => contentApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries(['content'])
    },
  })

  const handleDelete = (id, title) => {
    if (window.confirm(`Are you sure you want to delete "${title}"?`)) {
      deleteMutation.mutate(id)
    }
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Content</h1>
          <p className="text-gray-500 mt-1">Manage your articles, posts, and pages</p>
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
                className="input pl-10"
              />
            </div>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="input w-full sm:w-40"
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
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
            </div>
          ) : contentList && contentList.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200 bg-gray-50">
                    <th className="text-left py-3 px-6 text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Title
                    </th>
                    <th className="text-left py-3 px-6 text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="text-left py-3 px-6 text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Author
                    </th>
                    <th className="text-left py-3 px-6 text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Updated
                    </th>
                    <th className="text-right py-3 px-6 text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {contentList.map((item) => {
                    const StatusIcon = statusIcons[item.status] || Clock
                    return (
                      <tr key={item.id} className="hover:bg-gray-50">
                        <td className="py-4 px-6">
                          <div>
                            <Link
                              to={`/content/${item.id}`}
                              className="font-medium text-gray-900 hover:text-primary-600"
                            >
                              {item.title}
                            </Link>
                            {item.excerpt && (
                              <p className="text-sm text-gray-500 mt-1 line-clamp-1">
                                {item.excerpt}
                              </p>
                            )}
                          </div>
                        </td>
                        <td className="py-4 px-6">
                          <span
                            className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${
                              statusColors[item.status] || 'bg-gray-100 text-gray-700'
                            }`}
                          >
                            <StatusIcon className="h-3 w-3" />
                            {item.status.charAt(0).toUpperCase() + item.status.slice(1)}
                          </span>
                        </td>
                        <td className="py-4 px-6 text-sm text-gray-500">
                          {item.author?.username || 'Unknown'}
                        </td>
                        <td className="py-4 px-6 text-sm text-gray-500">
                          {new Date(item.updated_at).toLocaleDateString()}
                        </td>
                        <td className="py-4 px-6 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Link
                              to={`/content/${item.id}`}
                              className="p-2 text-gray-400 hover:text-primary-600 rounded-lg hover:bg-gray-100"
                            >
                              <Edit className="h-4 w-4" />
                            </Link>
                            <button
                              onClick={() => handleDelete(item.id, item.title)}
                              className="p-2 text-gray-400 hover:text-red-600 rounded-lg hover:bg-gray-100"
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
              <FileText className="h-12 w-12 text-gray-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-1">No content found</h3>
              <p className="text-gray-500 mb-4">Get started by creating your first piece of content</p>
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

// Missing import for FileText
import { FileText } from 'lucide-react'

export default ContentListPage
