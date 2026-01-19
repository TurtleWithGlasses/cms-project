import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { tagsApi } from '../../services/api'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import { Card, CardContent } from '../../components/ui/Card'
import {
  Search,
  Plus,
  Edit2,
  Trash2,
  Tag,
  X,
  FileText,
} from 'lucide-react'

function TagsPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [editingTag, setEditingTag] = useState(null)
  const [formData, setFormData] = useState({
    name: '',
    slug: '',
    color: '#6366f1',
  })

  // Predefined colors for tags
  const colorOptions = [
    '#6366f1', // indigo
    '#8b5cf6', // violet
    '#ec4899', // pink
    '#ef4444', // red
    '#f97316', // orange
    '#eab308', // yellow
    '#22c55e', // green
    '#14b8a6', // teal
    '#3b82f6', // blue
    '#6b7280', // gray
  ]

  // Fetch tags
  const { data: tags, isLoading } = useQuery({
    queryKey: ['tags', search],
    queryFn: () => tagsApi.getAll({ search }),
    select: (res) => res.data,
  })

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data) => tagsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries(['tags'])
      closeModal()
    },
  })

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }) => tagsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['tags'])
      closeModal()
    },
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id) => tagsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries(['tags'])
    },
  })

  const openCreateModal = () => {
    setEditingTag(null)
    setFormData({
      name: '',
      slug: '',
      color: '#6366f1',
    })
    setShowModal(true)
  }

  const openEditModal = (tag) => {
    setEditingTag(tag)
    setFormData({
      name: tag.name,
      slug: tag.slug,
      color: tag.color || '#6366f1',
    })
    setShowModal(true)
  }

  const closeModal = () => {
    setShowModal(false)
    setEditingTag(null)
    setFormData({
      name: '',
      slug: '',
      color: '#6366f1',
    })
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    const submitData = {
      ...formData,
      slug: formData.slug || formData.name.toLowerCase().replace(/\s+/g, '-'),
    }
    if (editingTag) {
      updateMutation.mutate({ id: editingTag.id, data: submitData })
    } else {
      createMutation.mutate(submitData)
    }
  }

  const handleDelete = (tag) => {
    if (window.confirm(`Delete tag "${tag.name}"?`)) {
      deleteMutation.mutate(tag.id)
    }
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Tags</h1>
          <p className="text-gray-500 mt-1">Manage tags for your content</p>
        </div>
        <Button onClick={openCreateModal}>
          <Plus className="h-4 w-4 mr-2" />
          Add Tag
        </Button>
      </div>

      {/* Search */}
      <Card>
        <CardContent className="pt-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search tags..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input pl-10"
            />
          </div>
        </CardContent>
      </Card>

      {/* Tags grid */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>
      ) : tags?.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Tag className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900">No tags</h3>
            <p className="text-gray-500 mt-1">Create your first tag to label content.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {tags?.map((tag) => (
            <Card key={tag.id} className="group hover:shadow-md transition-shadow">
              <CardContent className="p-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div
                      className="h-10 w-10 rounded-lg flex items-center justify-center"
                      style={{ backgroundColor: `${tag.color || '#6366f1'}20` }}
                    >
                      <Tag
                        className="h-5 w-5"
                        style={{ color: tag.color || '#6366f1' }}
                      />
                    </div>
                    <div>
                      <h3 className="font-medium text-gray-900">{tag.name}</h3>
                      <p className="text-sm text-gray-500">{tag.slug}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={() => openEditModal(tag)}
                      className="p-1.5 text-gray-600 hover:text-primary-600 hover:bg-gray-100 rounded"
                    >
                      <Edit2 className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(tag)}
                      className="p-1.5 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
                <div className="mt-3 flex items-center gap-2 text-sm text-gray-500">
                  <FileText className="h-4 w-4" />
                  <span>{tag.content_count || 0} posts</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <h2 className="text-lg font-semibold">
                {editingTag ? 'Edit Tag' : 'Create Tag'}
              </h2>
              <button
                onClick={closeModal}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <Input
                label="Name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
              />
              <Input
                label="Slug"
                value={formData.slug}
                onChange={(e) => setFormData({ ...formData, slug: e.target.value })}
                placeholder="auto-generated-from-name"
              />
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Color
                </label>
                <div className="flex flex-wrap gap-2">
                  {colorOptions.map((color) => (
                    <button
                      key={color}
                      type="button"
                      onClick={() => setFormData({ ...formData, color })}
                      className={`h-8 w-8 rounded-full border-2 transition-transform hover:scale-110 ${
                        formData.color === color
                          ? 'border-gray-900 scale-110'
                          : 'border-transparent'
                      }`}
                      style={{ backgroundColor: color }}
                    />
                  ))}
                </div>
              </div>
              <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                <div
                  className="h-8 w-8 rounded flex items-center justify-center"
                  style={{ backgroundColor: `${formData.color}20` }}
                >
                  <Tag className="h-4 w-4" style={{ color: formData.color }} />
                </div>
                <span
                  className="px-2 py-1 text-sm font-medium rounded"
                  style={{
                    backgroundColor: `${formData.color}20`,
                    color: formData.color,
                  }}
                >
                  {formData.name || 'Preview'}
                </span>
              </div>
              <div className="flex justify-end gap-3 pt-4">
                <Button type="button" variant="secondary" onClick={closeModal}>
                  Cancel
                </Button>
                <Button
                  type="submit"
                  isLoading={createMutation.isPending || updateMutation.isPending}
                >
                  {editingTag ? 'Update' : 'Create'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default TagsPage
