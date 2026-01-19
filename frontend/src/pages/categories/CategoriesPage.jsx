import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { categoriesApi } from '../../services/api'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import { Card, CardContent } from '../../components/ui/Card'
import {
  Search,
  Plus,
  Edit2,
  Trash2,
  Folder,
  FolderOpen,
  X,
  ChevronRight,
  FileText,
} from 'lucide-react'

function CategoriesPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [editingCategory, setEditingCategory] = useState(null)
  const [expandedCategories, setExpandedCategories] = useState(new Set())
  const [formData, setFormData] = useState({
    name: '',
    slug: '',
    description: '',
    parent_id: null,
  })

  // Fetch categories
  const { data: categories, isLoading } = useQuery({
    queryKey: ['categories', search],
    queryFn: () => categoriesApi.getAll({ search }),
    select: (res) => res.data,
  })

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data) => categoriesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries(['categories'])
      closeModal()
    },
  })

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }) => categoriesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['categories'])
      closeModal()
    },
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id) => categoriesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries(['categories'])
    },
  })

  const openCreateModal = (parentId = null) => {
    setEditingCategory(null)
    setFormData({
      name: '',
      slug: '',
      description: '',
      parent_id: parentId,
    })
    setShowModal(true)
  }

  const openEditModal = (category) => {
    setEditingCategory(category)
    setFormData({
      name: category.name,
      slug: category.slug,
      description: category.description || '',
      parent_id: category.parent_id,
    })
    setShowModal(true)
  }

  const closeModal = () => {
    setShowModal(false)
    setEditingCategory(null)
    setFormData({
      name: '',
      slug: '',
      description: '',
      parent_id: null,
    })
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    const submitData = {
      ...formData,
      slug: formData.slug || formData.name.toLowerCase().replace(/\s+/g, '-'),
    }
    if (editingCategory) {
      updateMutation.mutate({ id: editingCategory.id, data: submitData })
    } else {
      createMutation.mutate(submitData)
    }
  }

  const handleDelete = (category) => {
    if (window.confirm(`Delete category "${category.name}"? This may affect content using this category.`)) {
      deleteMutation.mutate(category.id)
    }
  }

  const toggleExpand = (categoryId) => {
    const newExpanded = new Set(expandedCategories)
    if (newExpanded.has(categoryId)) {
      newExpanded.delete(categoryId)
    } else {
      newExpanded.add(categoryId)
    }
    setExpandedCategories(newExpanded)
  }

  // Build category tree
  const buildTree = (items, parentId = null) => {
    return items
      ?.filter((item) => item.parent_id === parentId)
      .map((item) => ({
        ...item,
        children: buildTree(items, item.id),
      }))
  }

  const categoryTree = buildTree(categories)

  // Render category item with children
  const renderCategory = (category, level = 0) => {
    const hasChildren = category.children?.length > 0
    const isExpanded = expandedCategories.has(category.id)

    return (
      <div key={category.id}>
        <div
          className={`flex items-center gap-3 py-3 px-4 hover:bg-gray-50 border-b border-gray-100 ${
            level > 0 ? 'bg-gray-50/50' : ''
          }`}
          style={{ paddingLeft: `${level * 24 + 16}px` }}
        >
          {hasChildren ? (
            <button
              onClick={() => toggleExpand(category.id)}
              className="p-1 hover:bg-gray-200 rounded"
            >
              <ChevronRight
                className={`h-4 w-4 text-gray-400 transition-transform ${
                  isExpanded ? 'rotate-90' : ''
                }`}
              />
            </button>
          ) : (
            <span className="w-6" />
          )}

          {isExpanded ? (
            <FolderOpen className="h-5 w-5 text-primary-500" />
          ) : (
            <Folder className="h-5 w-5 text-gray-400" />
          )}

          <div className="flex-1 min-w-0">
            <p className="font-medium text-gray-900">{category.name}</p>
            <p className="text-sm text-gray-500 truncate">{category.slug}</p>
          </div>

          <div className="flex items-center gap-2 text-sm text-gray-500">
            <FileText className="h-4 w-4" />
            <span>{category.content_count || 0}</span>
          </div>

          <div className="flex items-center gap-1">
            <button
              onClick={() => openCreateModal(category.id)}
              className="p-2 text-gray-600 hover:text-primary-600 hover:bg-gray-100 rounded-lg"
              title="Add subcategory"
            >
              <Plus className="h-4 w-4" />
            </button>
            <button
              onClick={() => openEditModal(category)}
              className="p-2 text-gray-600 hover:text-primary-600 hover:bg-gray-100 rounded-lg"
            >
              <Edit2 className="h-4 w-4" />
            </button>
            <button
              onClick={() => handleDelete(category)}
              className="p-2 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        </div>

        {hasChildren && isExpanded && (
          <div>
            {category.children.map((child) => renderCategory(child, level + 1))}
          </div>
        )}
      </div>
    )
  }

  // Flatten categories for parent select
  const flattenCategories = (items, level = 0) => {
    let result = []
    items?.forEach((item) => {
      result.push({ ...item, level })
      if (item.children?.length > 0) {
        result = result.concat(flattenCategories(item.children, level + 1))
      }
    })
    return result
  }

  const flatCategories = flattenCategories(categoryTree)

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Categories</h1>
          <p className="text-gray-500 mt-1">Organize your content with categories</p>
        </div>
        <Button onClick={() => openCreateModal()}>
          <Plus className="h-4 w-4 mr-2" />
          Add Category
        </Button>
      </div>

      {/* Search */}
      <Card>
        <CardContent className="pt-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search categories..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input pl-10"
            />
          </div>
        </CardContent>
      </Card>

      {/* Categories tree */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
            </div>
          ) : categoryTree?.length === 0 ? (
            <div className="text-center py-12">
              <Folder className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900">No categories</h3>
              <p className="text-gray-500 mt-1">Create your first category to organize content.</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {categoryTree?.map((category) => renderCategory(category))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <h2 className="text-lg font-semibold">
                {editingCategory ? 'Edit Category' : 'Create Category'}
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
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Parent Category
                </label>
                <select
                  value={formData.parent_id || ''}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      parent_id: e.target.value ? parseInt(e.target.value) : null,
                    })
                  }
                  className="input"
                >
                  <option value="">None (Top Level)</option>
                  {flatCategories
                    ?.filter((c) => c.id !== editingCategory?.id)
                    .map((category) => (
                      <option key={category.id} value={category.id}>
                        {'—'.repeat(category.level)} {category.name}
                      </option>
                    ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Description
                </label>
                <textarea
                  rows={3}
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="input"
                  placeholder="Optional description..."
                />
              </div>
              <div className="flex justify-end gap-3 pt-4">
                <Button type="button" variant="secondary" onClick={closeModal}>
                  Cancel
                </Button>
                <Button
                  type="submit"
                  isLoading={createMutation.isPending || updateMutation.isPending}
                >
                  {editingCategory ? 'Update' : 'Create'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default CategoriesPage
