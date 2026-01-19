import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { webhooksApi } from '../../services/api'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import { Card, CardContent } from '../../components/ui/Card'
import {
  Webhook,
  Plus,
  Edit2,
  Trash2,
  X,
  CheckCircle,
  XCircle,
  RefreshCw,
  ExternalLink,
  Activity,
} from 'lucide-react'

function WebhooksPage() {
  const queryClient = useQueryClient()
  const [showModal, setShowModal] = useState(false)
  const [editingWebhook, setEditingWebhook] = useState(null)
  const [formData, setFormData] = useState({
    name: '',
    url: '',
    secret: '',
    events: [],
    is_active: true,
  })

  const eventOptions = [
    { value: 'content.created', label: 'Content Created', group: 'Content' },
    { value: 'content.updated', label: 'Content Updated', group: 'Content' },
    { value: 'content.deleted', label: 'Content Deleted', group: 'Content' },
    { value: 'content.published', label: 'Content Published', group: 'Content' },
    { value: 'user.created', label: 'User Created', group: 'Users' },
    { value: 'user.updated', label: 'User Updated', group: 'Users' },
    { value: 'user.deleted', label: 'User Deleted', group: 'Users' },
    { value: 'comment.created', label: 'Comment Created', group: 'Comments' },
    { value: 'comment.approved', label: 'Comment Approved', group: 'Comments' },
    { value: 'media.uploaded', label: 'Media Uploaded', group: 'Media' },
    { value: 'media.deleted', label: 'Media Deleted', group: 'Media' },
  ]

  // Fetch webhooks
  const { data: webhooks, isLoading } = useQuery({
    queryKey: ['webhooks'],
    queryFn: () => webhooksApi.getAll(),
    select: (res) => res.data,
  })

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data) => webhooksApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries(['webhooks'])
      closeModal()
    },
  })

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }) => webhooksApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['webhooks'])
      closeModal()
    },
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id) => webhooksApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries(['webhooks'])
    },
  })

  // Test webhook mutation
  const testMutation = useMutation({
    mutationFn: (id) => webhooksApi.test(id),
  })

  const openCreateModal = () => {
    setEditingWebhook(null)
    setFormData({
      name: '',
      url: '',
      secret: '',
      events: [],
      is_active: true,
    })
    setShowModal(true)
  }

  const openEditModal = (webhook) => {
    setEditingWebhook(webhook)
    setFormData({
      name: webhook.name,
      url: webhook.url,
      secret: '',
      events: webhook.events || [],
      is_active: webhook.is_active,
    })
    setShowModal(true)
  }

  const closeModal = () => {
    setShowModal(false)
    setEditingWebhook(null)
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    const submitData = { ...formData }
    if (editingWebhook && !submitData.secret) {
      delete submitData.secret
    }
    if (editingWebhook) {
      updateMutation.mutate({ id: editingWebhook.id, data: submitData })
    } else {
      createMutation.mutate(submitData)
    }
  }

  const handleDelete = (webhook) => {
    if (window.confirm(`Delete webhook "${webhook.name}"?`)) {
      deleteMutation.mutate(webhook.id)
    }
  }

  const handleTest = (webhook) => {
    testMutation.mutate(webhook.id)
  }

  const toggleEvent = (event) => {
    const events = formData.events.includes(event)
      ? formData.events.filter((e) => e !== event)
      : [...formData.events, event]
    setFormData({ ...formData, events })
  }

  const groupedEvents = eventOptions.reduce((acc, event) => {
    if (!acc[event.group]) acc[event.group] = []
    acc[event.group].push(event)
    return acc
  }, {})

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Webhooks</h1>
          <p className="text-gray-500 mt-1">Configure webhooks for real-time event notifications</p>
        </div>
        <Button onClick={openCreateModal}>
          <Plus className="h-4 w-4 mr-2" />
          Add Webhook
        </Button>
      </div>

      {/* Webhooks list */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>
      ) : webhooks?.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Webhook className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900">No webhooks</h3>
            <p className="text-gray-500 mt-1">Create a webhook to receive event notifications.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {webhooks?.map((webhook) => (
            <Card key={webhook.id}>
              <CardContent className="p-6">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-2">
                      <div
                        className={`h-10 w-10 rounded-lg flex items-center justify-center ${
                          webhook.is_active ? 'bg-green-100' : 'bg-gray-100'
                        }`}
                      >
                        <Webhook
                          className={`h-5 w-5 ${
                            webhook.is_active ? 'text-green-600' : 'text-gray-400'
                          }`}
                        />
                      </div>
                      <div>
                        <h3 className="font-medium text-gray-900">{webhook.name}</h3>
                        <div className="flex items-center gap-2 text-sm text-gray-500">
                          <ExternalLink className="h-3 w-3" />
                          <span className="truncate max-w-md">{webhook.url}</span>
                        </div>
                      </div>
                    </div>

                    {/* Events */}
                    <div className="flex flex-wrap gap-2 mt-3">
                      {webhook.events?.map((event) => (
                        <span
                          key={event}
                          className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-700 rounded"
                        >
                          {event}
                        </span>
                      ))}
                    </div>

                    {/* Status and stats */}
                    <div className="flex flex-wrap items-center gap-4 mt-4 text-sm">
                      <div className="flex items-center gap-1">
                        {webhook.is_active ? (
                          <>
                            <CheckCircle className="h-4 w-4 text-green-500" />
                            <span className="text-green-600">Active</span>
                          </>
                        ) : (
                          <>
                            <XCircle className="h-4 w-4 text-gray-400" />
                            <span className="text-gray-500">Inactive</span>
                          </>
                        )}
                      </div>
                      {webhook.last_triggered_at && (
                        <div className="flex items-center gap-1 text-gray-500">
                          <Activity className="h-4 w-4" />
                          <span>
                            Last triggered: {new Date(webhook.last_triggered_at).toLocaleString()}
                          </span>
                        </div>
                      )}
                      {webhook.success_count !== undefined && (
                        <div className="text-gray-500">
                          <span className="text-green-600">{webhook.success_count} successful</span>
                          {webhook.failure_count > 0 && (
                            <span className="text-red-600 ml-2">
                              {webhook.failure_count} failed
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => handleTest(webhook)}
                      isLoading={testMutation.isPending}
                    >
                      <RefreshCw className="h-4 w-4 mr-1" />
                      Test
                    </Button>
                    <button
                      onClick={() => openEditModal(webhook)}
                      className="p-2 text-gray-600 hover:text-primary-600 hover:bg-gray-100 rounded-lg"
                    >
                      <Edit2 className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(webhook)}
                      className="p-2 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-6 border-b border-gray-200 sticky top-0 bg-white">
              <h2 className="text-lg font-semibold">
                {editingWebhook ? 'Edit Webhook' : 'Create Webhook'}
              </h2>
              <button onClick={closeModal} className="p-2 hover:bg-gray-100 rounded-lg">
                <X className="h-5 w-5" />
              </button>
            </div>
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <Input
                label="Name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="e.g., Content Notification"
                required
              />

              <Input
                label="Endpoint URL"
                type="url"
                value={formData.url}
                onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                placeholder="https://example.com/webhook"
                required
              />

              <Input
                label={editingWebhook ? 'Secret (leave blank to keep current)' : 'Secret'}
                value={formData.secret}
                onChange={(e) => setFormData({ ...formData, secret: e.target.value })}
                placeholder="Webhook signing secret"
              />

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Events</label>
                <div className="border border-gray-200 rounded-lg divide-y divide-gray-200 max-h-60 overflow-y-auto">
                  {Object.entries(groupedEvents).map(([group, events]) => (
                    <div key={group} className="p-3">
                      <p className="text-xs font-medium text-gray-500 uppercase mb-2">{group}</p>
                      <div className="space-y-2">
                        {events.map((event) => (
                          <label key={event.value} className="flex items-center gap-2 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={formData.events.includes(event.value)}
                              onChange={() => toggleEvent(event.value)}
                              className="h-4 w-4 text-primary-600 rounded border-gray-300"
                            />
                            <span className="text-sm text-gray-700">{event.label}</span>
                          </label>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="is_active"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  className="h-4 w-4 text-primary-600 rounded border-gray-300"
                />
                <label htmlFor="is_active" className="text-sm text-gray-700">
                  Enable this webhook
                </label>
              </div>

              <div className="flex justify-end gap-3 pt-4">
                <Button type="button" variant="secondary" onClick={closeModal}>
                  Cancel
                </Button>
                <Button
                  type="submit"
                  isLoading={createMutation.isPending || updateMutation.isPending}
                  disabled={!formData.name || !formData.url || formData.events.length === 0}
                >
                  {editingWebhook ? 'Update' : 'Create'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default WebhooksPage
