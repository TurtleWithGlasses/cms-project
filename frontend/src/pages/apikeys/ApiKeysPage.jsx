import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiKeysApi } from '../../services/api'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card'
import {
  Key,
  Plus,
  Trash2,
  Copy,
  Eye,
  EyeOff,
  X,
  CheckCircle,
  Calendar,
  Activity,
} from 'lucide-react'

function ApiKeysPage() {
  const queryClient = useQueryClient()
  const [showModal, setShowModal] = useState(false)
  const [newKey, setNewKey] = useState(null)
  const [showKey, setShowKey] = useState({})
  const [formData, setFormData] = useState({
    name: '',
    expires_in_days: 365,
    scopes: ['read'],
  })

  const scopeOptions = [
    { value: 'read', label: 'Read', description: 'Read content and metadata' },
    { value: 'write', label: 'Write', description: 'Create and update content' },
    { value: 'delete', label: 'Delete', description: 'Delete content' },
    { value: 'admin', label: 'Admin', description: 'Full administrative access' },
  ]

  // Fetch API keys
  const { data: apiKeys, isLoading } = useQuery({
    queryKey: ['api-keys'],
    queryFn: () => apiKeysApi.getAll(),
    select: (res) => res.data,
  })

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data) => apiKeysApi.create(data),
    onSuccess: (res) => {
      setNewKey(res.data)
      queryClient.invalidateQueries(['api-keys'])
    },
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id) => apiKeysApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries(['api-keys'])
    },
  })

  const openModal = () => {
    setFormData({
      name: '',
      expires_in_days: 365,
      scopes: ['read'],
    })
    setNewKey(null)
    setShowModal(true)
  }

  const closeModal = () => {
    setShowModal(false)
    setNewKey(null)
    setFormData({
      name: '',
      expires_in_days: 365,
      scopes: ['read'],
    })
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    createMutation.mutate(formData)
  }

  const handleDelete = (apiKey) => {
    if (window.confirm(`Revoke API key "${apiKey.name}"? This cannot be undone.`)) {
      deleteMutation.mutate(apiKey.id)
    }
  }

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text)
  }

  const toggleScope = (scope) => {
    const scopes = formData.scopes.includes(scope)
      ? formData.scopes.filter((s) => s !== scope)
      : [...formData.scopes, scope]
    setFormData({ ...formData, scopes })
  }

  const toggleShowKey = (id) => {
    setShowKey((prev) => ({ ...prev, [id]: !prev[id] }))
  }

  const maskKey = (key) => {
    if (!key) return '••••••••••••••••'
    return key.substring(0, 8) + '••••••••' + key.substring(key.length - 4)
  }

  const formatDate = (date) => {
    if (!date) return 'Never'
    return new Date(date).toLocaleDateString()
  }

  const isExpired = (date) => {
    if (!date) return false
    return new Date(date) < new Date()
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">API Keys</h1>
          <p className="text-gray-500 mt-1">Manage API keys for external integrations</p>
        </div>
        <Button onClick={openModal}>
          <Plus className="h-4 w-4 mr-2" />
          Generate New Key
        </Button>
      </div>

      {/* Info card */}
      <Card className="bg-blue-50 border-blue-200">
        <CardContent className="py-4">
          <div className="flex items-start gap-3">
            <Key className="h-5 w-5 text-blue-600 mt-0.5" />
            <div className="text-sm text-blue-700">
              <p className="font-medium">Keep your API keys secure</p>
              <p className="mt-1">
                API keys grant access to your CMS. Never share them publicly or commit them to version control.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* API keys list */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
            </div>
          ) : apiKeys?.length === 0 ? (
            <div className="text-center py-12">
              <Key className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900">No API keys</h3>
              <p className="text-gray-500 mt-1">Generate your first API key to get started.</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-200">
              {apiKeys?.map((apiKey) => (
                <div key={apiKey.id} className="p-6">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="font-medium text-gray-900">{apiKey.name}</h3>
                        {isExpired(apiKey.expires_at) ? (
                          <span className="px-2 py-0.5 text-xs font-medium bg-red-100 text-red-700 rounded-full">
                            Expired
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 text-xs font-medium bg-green-100 text-green-700 rounded-full">
                            Active
                          </span>
                        )}
                      </div>

                      {/* Key display */}
                      <div className="flex items-center gap-2 bg-gray-100 rounded-lg px-3 py-2 font-mono text-sm mb-3">
                        <span className="flex-1 truncate">
                          {showKey[apiKey.id] ? apiKey.key : maskKey(apiKey.key_prefix)}
                        </span>
                        <button
                          onClick={() => toggleShowKey(apiKey.id)}
                          className="p-1 hover:bg-gray-200 rounded"
                          title={showKey[apiKey.id] ? 'Hide' : 'Show'}
                        >
                          {showKey[apiKey.id] ? (
                            <EyeOff className="h-4 w-4 text-gray-500" />
                          ) : (
                            <Eye className="h-4 w-4 text-gray-500" />
                          )}
                        </button>
                        <button
                          onClick={() => copyToClipboard(apiKey.key_prefix)}
                          className="p-1 hover:bg-gray-200 rounded"
                          title="Copy"
                        >
                          <Copy className="h-4 w-4 text-gray-500" />
                        </button>
                      </div>

                      {/* Scopes */}
                      <div className="flex flex-wrap gap-2 mb-3">
                        {apiKey.scopes?.map((scope) => (
                          <span
                            key={scope}
                            className="px-2 py-1 text-xs font-medium bg-gray-200 text-gray-700 rounded"
                          >
                            {scope}
                          </span>
                        ))}
                      </div>

                      {/* Meta info */}
                      <div className="flex flex-wrap items-center gap-4 text-sm text-gray-500">
                        <div className="flex items-center gap-1">
                          <Calendar className="h-4 w-4" />
                          <span>Created {formatDate(apiKey.created_at)}</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <Calendar className="h-4 w-4" />
                          <span>
                            Expires {apiKey.expires_at ? formatDate(apiKey.expires_at) : 'Never'}
                          </span>
                        </div>
                        {apiKey.last_used_at && (
                          <div className="flex items-center gap-1">
                            <Activity className="h-4 w-4" />
                            <span>Last used {formatDate(apiKey.last_used_at)}</span>
                          </div>
                        )}
                      </div>
                    </div>

                    <Button
                      variant="danger"
                      size="sm"
                      onClick={() => handleDelete(apiKey)}
                    >
                      <Trash2 className="h-4 w-4 mr-1" />
                      Revoke
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <h2 className="text-lg font-semibold">
                {newKey ? 'API Key Created' : 'Generate API Key'}
              </h2>
              <button onClick={closeModal} className="p-2 hover:bg-gray-100 rounded-lg">
                <X className="h-5 w-5" />
              </button>
            </div>

            {newKey ? (
              <div className="p-6">
                <div className="flex items-center gap-3 mb-4 text-green-600">
                  <CheckCircle className="h-6 w-6" />
                  <span className="font-medium">Key generated successfully!</span>
                </div>

                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4">
                  <p className="text-sm text-yellow-800">
                    <strong>Important:</strong> Copy this key now. You won't be able to see it again.
                  </p>
                </div>

                <div className="flex items-center gap-2 bg-gray-100 rounded-lg px-3 py-2 font-mono text-sm">
                  <span className="flex-1 break-all">{newKey.key}</span>
                  <button
                    onClick={() => copyToClipboard(newKey.key)}
                    className="p-1 hover:bg-gray-200 rounded flex-shrink-0"
                  >
                    <Copy className="h-4 w-4 text-gray-500" />
                  </button>
                </div>

                <div className="mt-6 flex justify-end">
                  <Button onClick={closeModal}>Done</Button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="p-6 space-y-4">
                <Input
                  label="Key Name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g., Production API Key"
                  required
                />

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Expires In
                  </label>
                  <select
                    value={formData.expires_in_days}
                    onChange={(e) =>
                      setFormData({ ...formData, expires_in_days: parseInt(e.target.value) })
                    }
                    className="input"
                  >
                    <option value={30}>30 days</option>
                    <option value={90}>90 days</option>
                    <option value={180}>180 days</option>
                    <option value={365}>1 year</option>
                    <option value={0}>Never</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Scopes
                  </label>
                  <div className="space-y-2">
                    {scopeOptions.map((scope) => (
                      <label
                        key={scope.value}
                        className="flex items-start gap-3 p-3 border border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50"
                      >
                        <input
                          type="checkbox"
                          checked={formData.scopes.includes(scope.value)}
                          onChange={() => toggleScope(scope.value)}
                          className="h-4 w-4 text-primary-600 rounded border-gray-300 mt-0.5"
                        />
                        <div>
                          <p className="font-medium text-gray-900">{scope.label}</p>
                          <p className="text-sm text-gray-500">{scope.description}</p>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>

                <div className="flex justify-end gap-3 pt-4">
                  <Button type="button" variant="secondary" onClick={closeModal}>
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    isLoading={createMutation.isPending}
                    disabled={!formData.name || formData.scopes.length === 0}
                  >
                    Generate Key
                  </Button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default ApiKeysPage
