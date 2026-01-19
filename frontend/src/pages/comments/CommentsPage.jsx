import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { commentsApi } from '../../services/api'
import Button from '../../components/ui/Button'
import { Card, CardContent } from '../../components/ui/Card'
import {
  Search,
  MessageSquare,
  Check,
  X,
  Trash2,
  Flag,
  User,
  Calendar,
  FileText,
  Filter,
  CheckCircle,
  XCircle,
  Clock,
} from 'lucide-react'

function CommentsPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [selectedComments, setSelectedComments] = useState(new Set())

  // Fetch comments
  const { data: commentsData, isLoading } = useQuery({
    queryKey: ['comments', search, statusFilter],
    queryFn: () => commentsApi.getAll({ search, status: statusFilter }),
    select: (res) => res.data,
  })

  const comments = commentsData?.items || commentsData || []

  // Approve mutation
  const approveMutation = useMutation({
    mutationFn: (id) => commentsApi.approve(id),
    onSuccess: () => {
      queryClient.invalidateQueries(['comments'])
    },
  })

  // Reject mutation
  const rejectMutation = useMutation({
    mutationFn: (id) => commentsApi.reject(id),
    onSuccess: () => {
      queryClient.invalidateQueries(['comments'])
    },
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id) => commentsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries(['comments'])
      setSelectedComments(new Set())
    },
  })

  // Bulk actions
  const handleBulkApprove = () => {
    selectedComments.forEach((id) => {
      approveMutation.mutate(id)
    })
    setSelectedComments(new Set())
  }

  const handleBulkReject = () => {
    selectedComments.forEach((id) => {
      rejectMutation.mutate(id)
    })
    setSelectedComments(new Set())
  }

  const handleBulkDelete = () => {
    if (window.confirm(`Delete ${selectedComments.size} selected comments?`)) {
      selectedComments.forEach((id) => {
        deleteMutation.mutate(id)
      })
    }
  }

  const toggleSelect = (id) => {
    const newSelected = new Set(selectedComments)
    if (newSelected.has(id)) {
      newSelected.delete(id)
    } else {
      newSelected.add(id)
    }
    setSelectedComments(newSelected)
  }

  const toggleSelectAll = () => {
    if (selectedComments.size === comments.length) {
      setSelectedComments(new Set())
    } else {
      setSelectedComments(new Set(comments.map((c) => c.id)))
    }
  }

  const getStatusBadge = (status) => {
    const styles = {
      pending: { bg: 'bg-yellow-100', text: 'text-yellow-700', icon: Clock },
      approved: { bg: 'bg-green-100', text: 'text-green-700', icon: CheckCircle },
      rejected: { bg: 'bg-red-100', text: 'text-red-700', icon: XCircle },
      spam: { bg: 'bg-gray-100', text: 'text-gray-700', icon: Flag },
    }
    const style = styles[status] || styles.pending
    const Icon = style.icon

    return (
      <span className={`inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full ${style.bg} ${style.text}`}>
        <Icon className="h-3 w-3" />
        {status}
      </span>
    )
  }

  // Stats
  const stats = {
    pending: comments.filter((c) => c.status === 'pending').length,
    approved: comments.filter((c) => c.status === 'approved').length,
    rejected: comments.filter((c) => c.status === 'rejected').length,
    spam: comments.filter((c) => c.status === 'spam').length,
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Comments</h1>
        <p className="text-gray-500 mt-1">Moderate and manage user comments</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card
          className={`cursor-pointer transition-colors ${statusFilter === 'pending' ? 'ring-2 ring-yellow-500' : ''}`}
          onClick={() => setStatusFilter(statusFilter === 'pending' ? '' : 'pending')}
        >
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-yellow-100 rounded-lg">
                <Clock className="h-5 w-5 text-yellow-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">{stats.pending}</p>
                <p className="text-sm text-gray-500">Pending</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card
          className={`cursor-pointer transition-colors ${statusFilter === 'approved' ? 'ring-2 ring-green-500' : ''}`}
          onClick={() => setStatusFilter(statusFilter === 'approved' ? '' : 'approved')}
        >
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-100 rounded-lg">
                <CheckCircle className="h-5 w-5 text-green-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">{stats.approved}</p>
                <p className="text-sm text-gray-500">Approved</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card
          className={`cursor-pointer transition-colors ${statusFilter === 'rejected' ? 'ring-2 ring-red-500' : ''}`}
          onClick={() => setStatusFilter(statusFilter === 'rejected' ? '' : 'rejected')}
        >
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-red-100 rounded-lg">
                <XCircle className="h-5 w-5 text-red-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">{stats.rejected}</p>
                <p className="text-sm text-gray-500">Rejected</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card
          className={`cursor-pointer transition-colors ${statusFilter === 'spam' ? 'ring-2 ring-gray-500' : ''}`}
          onClick={() => setStatusFilter(statusFilter === 'spam' ? '' : 'spam')}
        >
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-gray-100 rounded-lg">
                <Flag className="h-5 w-5 text-gray-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">{stats.spam}</p>
                <p className="text-sm text-gray-500">Spam</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters and bulk actions */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search comments..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="input pl-10"
                />
              </div>
            </div>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="input w-full sm:w-40"
            >
              <option value="">All Status</option>
              <option value="pending">Pending</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
              <option value="spam">Spam</option>
            </select>
          </div>
          {selectedComments.size > 0 && (
            <div className="mt-4 flex items-center gap-2 p-3 bg-gray-50 rounded-lg">
              <span className="text-sm text-gray-600">
                {selectedComments.size} selected
              </span>
              <div className="flex-1" />
              <Button size="sm" onClick={handleBulkApprove}>
                <Check className="h-4 w-4 mr-1" />
                Approve
              </Button>
              <Button size="sm" variant="secondary" onClick={handleBulkReject}>
                <X className="h-4 w-4 mr-1" />
                Reject
              </Button>
              <Button size="sm" variant="danger" onClick={handleBulkDelete}>
                <Trash2 className="h-4 w-4 mr-1" />
                Delete
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Comments list */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
            </div>
          ) : comments.length === 0 ? (
            <div className="text-center py-12">
              <MessageSquare className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900">No comments</h3>
              <p className="text-gray-500 mt-1">Comments will appear here when users post them.</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-200">
              {/* Header */}
              <div className="px-6 py-3 bg-gray-50 flex items-center gap-4">
                <input
                  type="checkbox"
                  checked={selectedComments.size === comments.length && comments.length > 0}
                  onChange={toggleSelectAll}
                  className="h-4 w-4 text-primary-600 rounded border-gray-300"
                />
                <span className="text-xs font-medium text-gray-500 uppercase">
                  {comments.length} comments
                </span>
              </div>

              {/* Comments */}
              {comments.map((comment) => (
                <div
                  key={comment.id}
                  className={`p-6 hover:bg-gray-50 ${
                    selectedComments.has(comment.id) ? 'bg-primary-50' : ''
                  }`}
                >
                  <div className="flex gap-4">
                    <input
                      type="checkbox"
                      checked={selectedComments.has(comment.id)}
                      onChange={() => toggleSelect(comment.id)}
                      className="h-4 w-4 text-primary-600 rounded border-gray-300 mt-1"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex items-center gap-3">
                          <div className="h-10 w-10 bg-gray-200 rounded-full flex items-center justify-center">
                            <User className="h-5 w-5 text-gray-500" />
                          </div>
                          <div>
                            <p className="font-medium text-gray-900">
                              {comment.author_name || 'Anonymous'}
                            </p>
                            <p className="text-sm text-gray-500">
                              {comment.author_email}
                            </p>
                          </div>
                        </div>
                        {getStatusBadge(comment.status)}
                      </div>

                      <p className="mt-3 text-gray-700">{comment.content}</p>

                      <div className="mt-3 flex flex-wrap items-center gap-4 text-sm text-gray-500">
                        <div className="flex items-center gap-1">
                          <FileText className="h-4 w-4" />
                          <span>{comment.content_title || 'Unknown post'}</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <Calendar className="h-4 w-4" />
                          <span>{new Date(comment.created_at).toLocaleString()}</span>
                        </div>
                      </div>

                      <div className="mt-4 flex items-center gap-2">
                        {comment.status === 'pending' && (
                          <>
                            <Button
                              size="sm"
                              onClick={() => approveMutation.mutate(comment.id)}
                              isLoading={approveMutation.isPending}
                            >
                              <Check className="h-4 w-4 mr-1" />
                              Approve
                            </Button>
                            <Button
                              size="sm"
                              variant="secondary"
                              onClick={() => rejectMutation.mutate(comment.id)}
                              isLoading={rejectMutation.isPending}
                            >
                              <X className="h-4 w-4 mr-1" />
                              Reject
                            </Button>
                          </>
                        )}
                        {comment.status === 'approved' && (
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => rejectMutation.mutate(comment.id)}
                          >
                            <X className="h-4 w-4 mr-1" />
                            Unapprove
                          </Button>
                        )}
                        {comment.status === 'rejected' && (
                          <Button
                            size="sm"
                            onClick={() => approveMutation.mutate(comment.id)}
                          >
                            <Check className="h-4 w-4 mr-1" />
                            Approve
                          </Button>
                        )}
                        <Button
                          size="sm"
                          variant="danger"
                          onClick={() => {
                            if (window.confirm('Delete this comment?')) {
                              deleteMutation.mutate(comment.id)
                            }
                          }}
                        >
                          <Trash2 className="h-4 w-4 mr-1" />
                          Delete
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default CommentsPage
