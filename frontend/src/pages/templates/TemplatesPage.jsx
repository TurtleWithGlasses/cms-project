import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { templatesApi } from '../../services/api'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card'
import {
  FileCode,
  Plus,
  Edit2,
  Trash2,
  Copy,
  X,
  Code,
  Eye,
} from 'lucide-react'

function TemplatesPage() {
  const queryClient = useQueryClient()
  const [showModal, setShowModal] = useState(false)
  const [editingTemplate, setEditingTemplate] = useState(null)
  const [previewTemplate, setPreviewTemplate] = useState(null)
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    content: '',
    type: 'page',
    is_default: false,
  })

  const typeOptions = [
    { value: 'page', label: 'Page' },
    { value: 'post', label: 'Blog Post' },
    { value: 'email', label: 'Email' },
    { value: 'newsletter', label: 'Newsletter' },
  ]

  // Fetch templates
  const { data: templates, isLoading } = useQuery({
    queryKey: ['templates'],
    queryFn: () => templatesApi.getAll(),
    select: (res) => res.data,
  })

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data) => templatesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries(['templates'])
      closeModal()
    },
  })

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }) => templatesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['templates'])
      closeModal()
    },
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id) => templatesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries(['templates'])
    },
  })

  // Duplicate mutation
  const duplicateMutation = useMutation({
    mutationFn: (id) => templatesApi.duplicate(id),
    onSuccess: () => {
      queryClient.invalidateQueries(['templates'])
    },
  })

  const openCreateModal = () => {
    setEditingTemplate(null)
    setFormData({
      name: '',
      description: '',
      content: getDefaultContent('page'),
      type: 'page',
      is_default: false,
    })
    setShowModal(true)
  }

  const openEditModal = (template) => {
    setEditingTemplate(template)
    setFormData({
      name: template.name,
      description: template.description || '',
      content: template.content || '',
      type: template.type || 'page',
      is_default: template.is_default || false,
    })
    setShowModal(true)
  }

  const closeModal = () => {
    setShowModal(false)
    setEditingTemplate(null)
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (editingTemplate) {
      updateMutation.mutate({ id: editingTemplate.id, data: formData })
    } else {
      createMutation.mutate(formData)
    }
  }

  const handleDelete = (template) => {
    if (window.confirm(`Delete template "${template.name}"?`)) {
      deleteMutation.mutate(template.id)
    }
  }

  const handleDuplicate = (template) => {
    duplicateMutation.mutate(template.id)
  }

  const getDefaultContent = (type) => {
    const defaults = {
      page: `<!DOCTYPE html>
<html>
<head>
  <title>{{title}}</title>
</head>
<body>
  <header>
    <h1>{{title}}</h1>
  </header>
  <main>
    {{content}}
  </main>
  <footer>
    <p>&copy; {{year}} Your Company</p>
  </footer>
</body>
</html>`,
      post: `<article>
  <header>
    <h1>{{title}}</h1>
    <p class="meta">By {{author}} on {{date}}</p>
  </header>
  <div class="content">
    {{content}}
  </div>
  <footer>
    <p>Tags: {{tags}}</p>
  </footer>
</article>`,
      email: `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
</head>
<body>
  <h1>{{subject}}</h1>
  <p>Hello {{name}},</p>
  <div>
    {{content}}
  </div>
  <p>Best regards,<br>Your Team</p>
</body>
</html>`,
      newsletter: `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
</head>
<body>
  <header>
    <h1>{{newsletter_title}}</h1>
    <p>{{date}}</p>
  </header>
  <main>
    {{content}}
  </main>
  <footer>
    <p><a href="{{unsubscribe_url}}">Unsubscribe</a></p>
  </footer>
</body>
</html>`,
    }
    return defaults[type] || defaults.page
  }

  const getTypeBadge = (type) => {
    const colors = {
      page: 'bg-blue-100 text-blue-700',
      post: 'bg-green-100 text-green-700',
      email: 'bg-purple-100 text-purple-700',
      newsletter: 'bg-orange-100 text-orange-700',
    }
    return (
      <span className={`px-2 py-1 text-xs font-medium rounded-full ${colors[type] || colors.page}`}>
        {type}
      </span>
    )
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Templates</h1>
          <p className="text-gray-500 mt-1">Create and manage content templates</p>
        </div>
        <Button onClick={openCreateModal}>
          <Plus className="h-4 w-4 mr-2" />
          New Template
        </Button>
      </div>

      {/* Templates grid */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>
      ) : templates?.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <FileCode className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900">No templates</h3>
            <p className="text-gray-500 mt-1">Create your first template to get started.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {templates?.map((template) => (
            <Card key={template.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 bg-gray-100 rounded-lg flex items-center justify-center">
                      <FileCode className="h-5 w-5 text-gray-600" />
                    </div>
                    <div>
                      <h3 className="font-medium text-gray-900">{template.name}</h3>
                      <div className="flex items-center gap-2 mt-1">
                        {getTypeBadge(template.type)}
                        {template.is_default && (
                          <span className="px-2 py-0.5 text-xs font-medium bg-yellow-100 text-yellow-700 rounded-full">
                            Default
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                {template.description && (
                  <p className="text-sm text-gray-500 mb-4 line-clamp-2">
                    {template.description}
                  </p>
                )}

                {/* Code preview */}
                <div className="bg-gray-900 rounded-lg p-3 mb-4 overflow-hidden">
                  <pre className="text-xs text-gray-300 line-clamp-4 font-mono">
                    {template.content?.substring(0, 200)}...
                  </pre>
                </div>

                <div className="flex items-center justify-between">
                  <button
                    onClick={() => setPreviewTemplate(template)}
                    className="text-sm text-primary-600 hover:text-primary-700 flex items-center gap-1"
                  >
                    <Eye className="h-4 w-4" />
                    Preview
                  </button>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => handleDuplicate(template)}
                      className="p-2 text-gray-600 hover:text-primary-600 hover:bg-gray-100 rounded-lg"
                      title="Duplicate"
                    >
                      <Copy className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => openEditModal(template)}
                      className="p-2 text-gray-600 hover:text-primary-600 hover:bg-gray-100 rounded-lg"
                    >
                      <Edit2 className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(template)}
                      className="p-2 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg"
                      disabled={template.is_default}
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
          <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-6 border-b border-gray-200 sticky top-0 bg-white">
              <h2 className="text-lg font-semibold">
                {editingTemplate ? 'Edit Template' : 'Create Template'}
              </h2>
              <button onClick={closeModal} className="p-2 hover:bg-gray-100 rounded-lg">
                <X className="h-5 w-5" />
              </button>
            </div>
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Input
                  label="Template Name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                />
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
                  <select
                    value={formData.type}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        type: e.target.value,
                        content: editingTemplate ? formData.content : getDefaultContent(e.target.value),
                      })
                    }
                    className="input"
                  >
                    {typeOptions.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <textarea
                  rows={2}
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="input"
                  placeholder="Optional description..."
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Template Content
                </label>
                <div className="relative">
                  <Code className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                  <textarea
                    rows={15}
                    value={formData.content}
                    onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                    className="input font-mono text-sm pl-10"
                    placeholder="Enter template HTML/content..."
                  />
                </div>
                <p className="mt-1 text-xs text-gray-500">
                  Use variables like {'{{title}}'}, {'{{content}}'}, {'{{author}}'}, {'{{date}}'}
                </p>
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="is_default"
                  checked={formData.is_default}
                  onChange={(e) => setFormData({ ...formData, is_default: e.target.checked })}
                  className="h-4 w-4 text-primary-600 rounded border-gray-300"
                />
                <label htmlFor="is_default" className="text-sm text-gray-700">
                  Set as default template for this type
                </label>
              </div>

              <div className="flex justify-end gap-3 pt-4">
                <Button type="button" variant="secondary" onClick={closeModal}>
                  Cancel
                </Button>
                <Button
                  type="submit"
                  isLoading={createMutation.isPending || updateMutation.isPending}
                >
                  {editingTemplate ? 'Update' : 'Create'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Preview Modal */}
      {previewTemplate && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl mx-4 max-h-[90vh] overflow-hidden flex flex-col">
            <div className="flex items-center justify-between p-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold">{previewTemplate.name}</h2>
              <button
                onClick={() => setPreviewTemplate(null)}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="flex-1 overflow-auto p-4 bg-gray-900">
              <pre className="text-sm text-gray-100 font-mono whitespace-pre-wrap">
                {previewTemplate.content}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default TemplatesPage
