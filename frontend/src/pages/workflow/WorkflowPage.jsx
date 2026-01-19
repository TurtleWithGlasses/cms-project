import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { workflowApi, contentApi } from '../../services/api'
import { useToast } from '../../components/ui/Toast'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card'
import Button from '../../components/ui/Button'
import {
  GitBranch,
  ArrowRight,
  FileText,
  Clock,
  User,
  Check,
  X,
  MessageSquare,
  Eye,
  Send,
  RotateCcw,
} from 'lucide-react'

// Mock data for demo
const mockPendingContent = [
  {
    id: 1,
    title: 'New Product Launch Announcement',
    status: 'pending_review',
    author: 'John Doe',
    submittedAt: '2024-01-18T10:30:00Z',
    currentStage: 'Editorial Review',
    comments: 2,
  },
  {
    id: 2,
    title: 'Q4 Financial Report',
    status: 'pending_review',
    author: 'Sarah Smith',
    submittedAt: '2024-01-17T15:45:00Z',
    currentStage: 'Legal Review',
    comments: 5,
  },
  {
    id: 3,
    title: 'Updated Privacy Policy',
    status: 'pending_approval',
    author: 'Mike Johnson',
    submittedAt: '2024-01-17T09:00:00Z',
    currentStage: 'Final Approval',
    comments: 3,
  },
  {
    id: 4,
    title: 'Blog Post: Industry Trends 2024',
    status: 'draft',
    author: 'Emma Wilson',
    submittedAt: '2024-01-16T14:20:00Z',
    currentStage: 'Draft',
    comments: 0,
  },
]

const workflowStages = [
  { id: 'draft', name: 'Draft', color: 'bg-gray-500' },
  { id: 'pending_review', name: 'Pending Review', color: 'bg-yellow-500' },
  { id: 'in_review', name: 'In Review', color: 'bg-blue-500' },
  { id: 'pending_approval', name: 'Pending Approval', color: 'bg-purple-500' },
  { id: 'approved', name: 'Approved', color: 'bg-green-500' },
  { id: 'published', name: 'Published', color: 'bg-green-600' },
  { id: 'rejected', name: 'Rejected', color: 'bg-red-500' },
]

function StatusBadge({ status }) {
  const stage = workflowStages.find((s) => s.id === status) || workflowStages[0]
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium text-white ${stage.color}`}>
      {stage.name}
    </span>
  )
}

function WorkflowPage() {
  const queryClient = useQueryClient()
  const toast = useToast()
  const [selectedContent, setSelectedContent] = useState(null)
  const [reviewComment, setReviewComment] = useState('')
  const [filter, setFilter] = useState('all')

  // Fetch pending content
  const { data: pendingContent = mockPendingContent, isLoading } = useQuery({
    queryKey: ['workflow-content', filter],
    queryFn: () => workflowApi.getPending({ status: filter }),
    select: (res) => res.data || mockPendingContent,
    placeholderData: mockPendingContent,
  })

  // Approve mutation
  const approveMutation = useMutation({
    mutationFn: ({ id, comment }) => workflowApi.approve(id, { comment }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflow-content'] })
      toast.success('Content approved successfully')
      setSelectedContent(null)
      setReviewComment('')
    },
    onError: () => toast.error('Failed to approve content'),
  })

  // Reject mutation
  const rejectMutation = useMutation({
    mutationFn: ({ id, comment }) => workflowApi.reject(id, { comment }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflow-content'] })
      toast.success('Content sent back for revision')
      setSelectedContent(null)
      setReviewComment('')
    },
    onError: () => toast.error('Failed to reject content'),
  })

  // Publish mutation
  const publishMutation = useMutation({
    mutationFn: (id) => contentApi.publish(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflow-content'] })
      toast.success('Content published successfully')
      setSelectedContent(null)
    },
    onError: () => toast.error('Failed to publish content'),
  })

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const filteredContent = filter === 'all'
    ? pendingContent
    : pendingContent.filter((c) => c.status === filter)

  const getStageActions = (status) => {
    switch (status) {
      case 'draft':
        return ['submit_for_review']
      case 'pending_review':
        return ['start_review', 'reject']
      case 'in_review':
        return ['approve', 'request_changes']
      case 'pending_approval':
        return ['approve', 'reject']
      case 'approved':
        return ['publish', 'unpublish']
      default:
        return []
    }
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Content Workflow</h1>
          <p className="text-gray-500 mt-1">Review and approve content before publishing</p>
        </div>
      </div>

      {/* Workflow pipeline visualization */}
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-between overflow-x-auto pb-2">
            {workflowStages.slice(0, -1).map((stage, index) => (
              <div key={stage.id} className="flex items-center">
                <div className="flex flex-col items-center min-w-[100px]">
                  <div className={`h-10 w-10 rounded-full ${stage.color} flex items-center justify-center text-white text-sm font-medium`}>
                    {pendingContent.filter((c) => c.status === stage.id).length}
                  </div>
                  <span className="text-xs text-gray-600 mt-2 text-center">{stage.name}</span>
                </div>
                {index < workflowStages.length - 2 && (
                  <ArrowRight className="h-5 w-5 text-gray-300 mx-2" />
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Filter tabs */}
      <div className="flex border-b border-gray-200 overflow-x-auto">
        <button
          onClick={() => setFilter('all')}
          className={`px-4 py-2 text-sm font-medium whitespace-nowrap ${
            filter === 'all'
              ? 'border-b-2 border-primary-600 text-primary-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          All ({pendingContent.length})
        </button>
        {workflowStages.slice(0, -2).map((stage) => {
          const count = pendingContent.filter((c) => c.status === stage.id).length
          return (
            <button
              key={stage.id}
              onClick={() => setFilter(stage.id)}
              className={`px-4 py-2 text-sm font-medium whitespace-nowrap ${
                filter === stage.id
                  ? 'border-b-2 border-primary-600 text-primary-600'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {stage.name} ({count})
            </button>
          )
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Content list */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <GitBranch className="h-5 w-5" />
                Pending Items
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {filteredContent.length === 0 ? (
                <div className="p-8 text-center text-gray-500">
                  <Check className="h-12 w-12 mx-auto mb-4 text-green-500" />
                  <p>No items pending review</p>
                </div>
              ) : (
                <div className="divide-y divide-gray-200">
                  {filteredContent.map((content) => (
                    <button
                      key={content.id}
                      onClick={() => setSelectedContent(content)}
                      className={`w-full text-left px-6 py-4 hover:bg-gray-50 transition-colors ${
                        selectedContent?.id === content.id ? 'bg-primary-50' : ''
                      }`}
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <FileText className="h-4 w-4 text-gray-400" />
                            <h3 className="font-medium text-gray-900 truncate">{content.title}</h3>
                          </div>
                          <div className="flex items-center gap-4 text-sm text-gray-500">
                            <span className="flex items-center gap-1">
                              <User className="h-3 w-3" />
                              {content.author}
                            </span>
                            <span className="flex items-center gap-1">
                              <Clock className="h-3 w-3" />
                              {formatDate(content.submittedAt)}
                            </span>
                            {content.comments > 0 && (
                              <span className="flex items-center gap-1">
                                <MessageSquare className="h-3 w-3" />
                                {content.comments}
                              </span>
                            )}
                          </div>
                        </div>
                        <StatusBadge status={content.status} />
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Review panel */}
        <div className="lg:col-span-1">
          <Card className="sticky top-24">
            <CardHeader>
              <CardTitle>Review Panel</CardTitle>
            </CardHeader>
            <CardContent>
              {selectedContent ? (
                <div className="space-y-4">
                  <div>
                    <h3 className="font-medium text-gray-900">{selectedContent.title}</h3>
                    <p className="text-sm text-gray-500 mt-1">
                      By {selectedContent.author} &bull; {formatDate(selectedContent.submittedAt)}
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-sm text-gray-500">Current Stage:</span>
                    <StatusBadge status={selectedContent.status} />
                  </div>

                  <div className="pt-4 border-t border-gray-200">
                    <Button variant="outline" className="w-full mb-3">
                      <Eye className="h-4 w-4 mr-2" />
                      Preview Content
                    </Button>

                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Review Comment
                    </label>
                    <textarea
                      rows={3}
                      value={reviewComment}
                      onChange={(e) => setReviewComment(e.target.value)}
                      placeholder="Add a comment for the author..."
                      className="input"
                    />
                  </div>

                  <div className="flex flex-col gap-2 pt-4 border-t border-gray-200">
                    {selectedContent.status === 'pending_approval' || selectedContent.status === 'in_review' ? (
                      <>
                        <Button
                          onClick={() => approveMutation.mutate({ id: selectedContent.id, comment: reviewComment })}
                          disabled={approveMutation.isPending}
                          className="w-full"
                        >
                          <Check className="h-4 w-4 mr-2" />
                          Approve
                        </Button>
                        <Button
                          variant="outline"
                          onClick={() => rejectMutation.mutate({ id: selectedContent.id, comment: reviewComment })}
                          disabled={rejectMutation.isPending}
                          className="w-full text-red-600 hover:text-red-700"
                        >
                          <RotateCcw className="h-4 w-4 mr-2" />
                          Request Changes
                        </Button>
                      </>
                    ) : selectedContent.status === 'approved' ? (
                      <Button
                        onClick={() => publishMutation.mutate(selectedContent.id)}
                        disabled={publishMutation.isPending}
                        className="w-full"
                      >
                        <Send className="h-4 w-4 mr-2" />
                        Publish Now
                      </Button>
                    ) : selectedContent.status === 'pending_review' ? (
                      <Button
                        onClick={() => approveMutation.mutate({ id: selectedContent.id, comment: reviewComment })}
                        disabled={approveMutation.isPending}
                        className="w-full"
                      >
                        <Check className="h-4 w-4 mr-2" />
                        Start Review
                      </Button>
                    ) : null}
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">
                  <GitBranch className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                  <p>Select an item to review</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

export default WorkflowPage
