import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { contentApi } from '../../services/api'
import { useToast } from '../../components/ui/Toast'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card'
import Button from '../../components/ui/Button'
import {
  History,
  Clock,
  User,
  Eye,
  RotateCcw,
  ChevronLeft,
  GitCompare,
  FileText,
  Check,
  ArrowLeft,
} from 'lucide-react'

// Mock data for demo
const mockRevisions = [
  {
    id: 1,
    version: 5,
    createdAt: '2024-01-18T14:30:00Z',
    author: 'John Doe',
    changes: 'Updated introduction paragraph and fixed typos',
    isCurrent: true,
  },
  {
    id: 2,
    version: 4,
    createdAt: '2024-01-17T10:15:00Z',
    author: 'Sarah Smith',
    changes: 'Added new section about features',
    isCurrent: false,
  },
  {
    id: 3,
    version: 3,
    createdAt: '2024-01-15T16:45:00Z',
    author: 'John Doe',
    changes: 'Restructured content layout',
    isCurrent: false,
  },
  {
    id: 4,
    version: 2,
    createdAt: '2024-01-12T09:00:00Z',
    author: 'Mike Johnson',
    changes: 'Initial content draft',
    isCurrent: false,
  },
  {
    id: 5,
    version: 1,
    createdAt: '2024-01-10T11:30:00Z',
    author: 'John Doe',
    changes: 'Created content',
    isCurrent: false,
  },
]

const mockContent = {
  id: 1,
  title: 'Getting Started with React',
  status: 'published',
}

function ContentRevisionsPage() {
  const { id } = useParams()
  const queryClient = useQueryClient()
  const toast = useToast()
  const [selectedRevision, setSelectedRevision] = useState(null)
  const [compareMode, setCompareMode] = useState(false)
  const [compareWith, setCompareWith] = useState(null)

  // Fetch content details
  const { data: content = mockContent } = useQuery({
    queryKey: ['content', id],
    queryFn: () => contentApi.getById(id),
    select: (res) => res.data || mockContent,
    placeholderData: mockContent,
  })

  // Fetch revisions
  const { data: revisions = mockRevisions, isLoading } = useQuery({
    queryKey: ['content-revisions', id],
    queryFn: () => contentApi.getRevisions(id),
    select: (res) => res.data || mockRevisions,
    placeholderData: mockRevisions,
  })

  // Restore revision mutation
  const restoreMutation = useMutation({
    mutationFn: (revisionId) => contentApi.restoreRevision(id, revisionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['content-revisions', id] })
      queryClient.invalidateQueries({ queryKey: ['content', id] })
      toast.success('Revision restored successfully')
      setSelectedRevision(null)
    },
    onError: () => toast.error('Failed to restore revision'),
  })

  const formatDate = (dateString) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const getRelativeTime = (dateString) => {
    const date = new Date(dateString)
    const now = new Date()
    const diff = now - date
    const days = Math.floor(diff / (1000 * 60 * 60 * 24))
    const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))

    if (days > 0) return `${days} day${days > 1 ? 's' : ''} ago`
    if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''} ago`
    return 'Just now'
  }

  const handleRestore = (revision) => {
    if (window.confirm(`Restore version ${revision.version}? This will create a new revision with the old content.`)) {
      restoreMutation.mutate(revision.id)
    }
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-sm text-gray-500 mb-2">
            <Link to="/content" className="hover:text-gray-700">Content</Link>
            <ChevronLeft className="h-4 w-4 rotate-180" />
            <Link to={`/content/${id}`} className="hover:text-gray-700">{content.title}</Link>
            <ChevronLeft className="h-4 w-4 rotate-180" />
            <span>Revisions</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Revision History</h1>
          <p className="text-gray-500 mt-1">{revisions.length} versions available</p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant={compareMode ? 'primary' : 'outline'}
            onClick={() => {
              setCompareMode(!compareMode)
              setCompareWith(null)
            }}
          >
            <GitCompare className="h-4 w-4 mr-2" />
            {compareMode ? 'Exit Compare' : 'Compare Versions'}
          </Button>
          <Link to={`/content/${id}`}>
            <Button variant="outline">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Editor
            </Button>
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Revisions list */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <History className="h-5 w-5" />
              Versions
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-gray-200 max-h-[600px] overflow-y-auto">
              {revisions.map((revision) => (
                <button
                  key={revision.id}
                  onClick={() => {
                    if (compareMode && selectedRevision) {
                      setCompareWith(revision)
                    } else {
                      setSelectedRevision(revision)
                    }
                  }}
                  className={`w-full text-left px-4 py-4 hover:bg-gray-50 transition-colors ${
                    selectedRevision?.id === revision.id ? 'bg-primary-50' :
                    compareWith?.id === revision.id ? 'bg-blue-50' : ''
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-900">Version {revision.version}</span>
                      {revision.isCurrent && (
                        <span className="text-xs px-2 py-0.5 bg-green-100 text-green-700 rounded-full">
                          Current
                        </span>
                      )}
                    </div>
                    {compareMode && selectedRevision && !revision.isCurrent && selectedRevision.id !== revision.id && (
                      <span className="text-xs text-primary-600">Click to compare</span>
                    )}
                  </div>
                  <div className="flex items-center gap-3 text-sm text-gray-500">
                    <span className="flex items-center gap-1">
                      <User className="h-3 w-3" />
                      {revision.author}
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {getRelativeTime(revision.createdAt)}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 mt-2 line-clamp-2">{revision.changes}</p>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Revision details / preview */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>
              {compareMode && compareWith
                ? `Comparing Version ${selectedRevision?.version} with Version ${compareWith.version}`
                : selectedRevision
                ? `Version ${selectedRevision.version} Details`
                : 'Select a Version'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {selectedRevision ? (
              <div className="space-y-6">
                {/* Revision metadata */}
                <div className="grid grid-cols-2 gap-4 p-4 bg-gray-50 rounded-lg">
                  <div>
                    <p className="text-sm text-gray-500">Created</p>
                    <p className="font-medium">{formatDate(selectedRevision.createdAt)}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Author</p>
                    <p className="font-medium">{selectedRevision.author}</p>
                  </div>
                  <div className="col-span-2">
                    <p className="text-sm text-gray-500">Change Summary</p>
                    <p className="font-medium">{selectedRevision.changes}</p>
                  </div>
                </div>

                {/* Compare view */}
                {compareMode && compareWith ? (
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <h4 className="font-medium text-gray-900 mb-2 flex items-center gap-2">
                        Version {selectedRevision.version}
                        {selectedRevision.isCurrent && (
                          <span className="text-xs px-2 py-0.5 bg-green-100 text-green-700 rounded-full">
                            Current
                          </span>
                        )}
                      </h4>
                      <div className="bg-gray-50 rounded-lg p-4 h-64 overflow-y-auto">
                        <p className="text-sm text-gray-600">
                          Content from version {selectedRevision.version} would be displayed here.
                          In a real implementation, this would show the actual content diff.
                        </p>
                      </div>
                    </div>
                    <div>
                      <h4 className="font-medium text-gray-900 mb-2 flex items-center gap-2">
                        Version {compareWith.version}
                        {compareWith.isCurrent && (
                          <span className="text-xs px-2 py-0.5 bg-green-100 text-green-700 rounded-full">
                            Current
                          </span>
                        )}
                      </h4>
                      <div className="bg-gray-50 rounded-lg p-4 h-64 overflow-y-auto">
                        <p className="text-sm text-gray-600">
                          Content from version {compareWith.version} would be displayed here.
                          Differences would be highlighted.
                        </p>
                      </div>
                    </div>
                  </div>
                ) : (
                  /* Single revision preview */
                  <div>
                    <h4 className="font-medium text-gray-900 mb-2">Content Preview</h4>
                    <div className="bg-gray-50 rounded-lg p-4 min-h-[200px]">
                      <div className="prose prose-sm max-w-none">
                        <p className="text-gray-600">
                          This is a preview of the content from version {selectedRevision.version}.
                          In a real implementation, the actual HTML/markdown content would be rendered here.
                        </p>
                        <p className="text-gray-600 mt-4">
                          The revision system tracks all changes made to content, allowing you to:
                        </p>
                        <ul className="text-gray-600">
                          <li>View previous versions of your content</li>
                          <li>Compare different versions side by side</li>
                          <li>Restore any previous version if needed</li>
                          <li>Track who made changes and when</li>
                        </ul>
                      </div>
                    </div>
                  </div>
                )}

                {/* Actions */}
                <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200">
                  <Button variant="outline">
                    <Eye className="h-4 w-4 mr-2" />
                    Full Preview
                  </Button>
                  {!selectedRevision.isCurrent && (
                    <Button
                      onClick={() => handleRestore(selectedRevision)}
                      disabled={restoreMutation.isPending}
                    >
                      <RotateCcw className="h-4 w-4 mr-2" />
                      Restore This Version
                    </Button>
                  )}
                </div>
              </div>
            ) : (
              <div className="text-center py-12 text-gray-500">
                <History className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                <p>Select a version from the list to view details</p>
                {compareMode && (
                  <p className="text-sm mt-2">Select two versions to compare them</p>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default ContentRevisionsPage
