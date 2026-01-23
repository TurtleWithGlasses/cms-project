import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { commentsApi } from '../../services/api'
import Button from '../../components/ui/Button'
import { Card, CardContent } from '../../components/ui/Card'
import { useToast } from '../../components/ui/Toast'
import { SkeletonComment } from '../../components/ui/Skeleton'
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
  CheckCircle,
  XCircle,
  Clock,
  AlertCircle,
  RefreshCw,
} from 'lucide-react'

function CommentsPage() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [selectedComments, setSelectedComments] = useState(new Set())

  // Fetch comments
  const { data: commentsData, isLoading, error, refetch } = useQuery({
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
      toast({
        title: 'Comment approved',
        description: 'The comment has been approved successfully.',
        variant: 'success',
      })
    },
    onError: (error) => {
      toast({
        title: 'Failed to approve',
        description: error.response?.data?.detail || error.message || 'An error occurred while approving the comment.',
        variant: 'error',
      })
    },
  })

  // Reject mutation
  const rejectMutation = useMutation({
    mutationFn: (id) => commentsApi.reject(id),
    onSuccess: () => {
      queryClient.invalidateQueries(['comments'])
      toast({
        title: 'Comment rejected',
        description: 'The comment has been rejected successfully.',
        variant: 'success',
      })
    },
    onError: (error) => {
      toast({
        title: 'Failed to reject',
        description: error.response?.data?.detail || error.message || 'An error occurred while rejecting the comment.',
        variant: 'error',
      })
    },
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id) => commentsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries(['comments'])
      setSelectedComments(new Set())
      toast({
        title: 'Comment deleted',
        description: 'The comment has been deleted successfully.',
        variant: 'success',
      })
    },
    onError: (error) => {
      toast({
        title: 'Failed to delete',
        description: error.response?.data?.detail || error.message || 'An error occurred while deleting the comment.',
        variant: 'error',
      })
    },
  })

  // Bulk actions
  const handleBulkApprove = () => {
    let successCount = 0
    selectedComments.forEach((id) => {
      approveMutation.mutate(id, {
        onSuccess: () => {
          successCount++
          if (successCount === selectedComments.size) {
            toast({
              title: 'Bulk approve complete',
              description: `${successCount} comment(s) approved.`,
              variant: 'success',
            })
          }
        },
      })
    })
    setSelectedComments(new Set())
  }

  const handleBulkReject = () => {
    let successCount = 0
    selectedComments.forEach((id) => {
      rejectMutation.mutate(id, {
        onSuccess: () => {
          successCount++
          if (successCount === selectedComments.size) {
            toast({
              title: 'Bulk reject complete',
              description: `${successCount} comment(s) rejected.`,
              variant: 'success',
            })
          }
        },
      })
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
      pending: { bg: 'bg-yellow-100 dark:bg-yellow-900/30', text: 'text-yellow-700 dark:text-yellow-400', icon: Clock },
      approved: { bg: 'bg-green-100 dark:bg-green-900/30', text: 'text-green-700 dark:text-green-400', icon: CheckCircle },
      rejected: { bg: 'bg-red-100 dark:bg-red-900/30', text: 'text-red-700 dark:text-red-400', icon: XCircle },
      spam: { bg: 'bg-gray-100 dark:bg-gray-700', text: 'text-gray-700 dark:text-gray-300', icon: Flag },
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

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Comments</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">Moderate and manage user comments</p>
        </div>
        <div className="flex flex-col items-center justify-center py-16 space-y-4">
          <AlertCircle className="h-12 w-12 text-red-500" />
          <div className="text-center">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Failed to load comments</h2>
            <p className="text-gray-600 dark:text-gray-400 mt-1">
              {error.response?.data?.detail || error.message || 'An error occurred while loading comments.'}
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
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Comments</h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">Moderate and manage user comments</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card
          className={`cursor-pointer transition-colors ${statusFilter === 'pending' ? 'ring-2 ring-yellow-500' : ''}`}
          onClick={() => setStatusFilter(statusFilter === 'pending' ? '' : 'pending')}
        >
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-yellow-100 dark:bg-yellow-900/30 rounded-lg">
                <Clock className="h-5 w-5 text-yellow-600 dark:text-yellow-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats.pending}</p>
                <p className="text-sm text-gray-500 dark:text-gray-400">Pending</p>
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
              <div className="p-2 bg-green-100 dark:bg-green-900/30 rounded-lg">
                <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats.approved}</p>
                <p className="text-sm text-gray-500 dark:text-gray-400">Approved</p>
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
              <div className="p-2 bg-red-100 dark:bg-red-900/30 rounded-lg">
                <XCircle className="h-5 w-5 text-red-600 dark:text-red-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats.rejected}</p>
                <p className="text-sm text-gray-500 dark:text-gray-400">Rejected</p>
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
              <div className="p-2 bg-gray-100 dark:bg-gray-700 rounded-lg">
                <Flag className="h-5 w-5 text-gray-600 dark:text-gray-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats.spam}</p>
                <p className="text-sm text-gray-500 dark:text-gray-400">Spam</p>
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
                  className="input pl-10 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                />
              </div>
            </div>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="input w-full sm:w-40 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
            >
              <option value="">All Status</option>
              <option value="pending">Pending</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
              <option value="spam">Spam</option>
            </select>
          </div>
          {selectedComments.size > 0 && (
            <div className="mt-4 flex items-center gap-2 p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
              <span className="text-sm text-gray-600 dark:text-gray-400">
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
            <div>
              {Array.from({ length: 3 }).map((_, i) => (
                <SkeletonComment key={i} />
              ))}
            </div>
          ) : comments.length === 0 ? (
            <div className="text-center py-12">
              <MessageSquare className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">No comments</h3>
              <p className="text-gray-500 dark:text-gray-400 mt-1">Comments will appear here when users post them.</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-200 dark:divide-gray-700">
              {/* Header */}
              <div className="px-6 py-3 bg-gray-50 dark:bg-gray-800 flex items-center gap-4">
                <input
                  type="checkbox"
                  checked={selectedComments.size === comments.length && comments.length > 0}
                  onChange={toggleSelectAll}
                  className="h-4 w-4 text-primary-600 rounded border-gray-300"
                />
                <span className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  {comments.length} comments
                </span>
              </div>

              {/* Comments */}
              {comments.map((comment) => (
                <div
                  key={comment.id}
                  className={`p-6 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors ${
                    selectedComments.has(comment.id) ? 'bg-primary-50 dark:bg-primary-900/20' : ''
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
                          <div className="h-10 w-10 bg-gray-200 dark:bg-gray-700 rounded-full flex items-center justify-center">
                            <User className="h-5 w-5 text-gray-500 dark:text-gray-400" />
                          </div>
                          <div>
                            <p className="font-medium text-gray-900 dark:text-white">
                              {comment.author_name || 'Anonymous'}
                            </p>
                            <p className="text-sm text-gray-500 dark:text-gray-400">
                              {comment.author_email}
                            </p>
                          </div>
                        </div>
                        {getStatusBadge(comment.status)}
                      </div>

                      <p className="mt-3 text-gray-700 dark:text-gray-300">{comment.content}</p>

                      <div className="mt-3 flex flex-wrap items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
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
                          disabled={deleteMutation.isPending}
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
