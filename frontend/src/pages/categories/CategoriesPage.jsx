import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { categoriesApi } from '../../services/api'
import { useToast } from '../../components/ui/Toast'
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
  AlertCircle,
  RefreshCw,
} from 'lucide-react'

// Validation schema for category form
const categorySchema = z.object({
  name: z.string()
    .min(1, 'Name is required')
    .min(2, 'Name must be at least 2 characters')
    .max(100, 'Name must be less than 100 characters'),
  slug: z.string()
    .max(100, 'Slug must be less than 100 characters')
    .regex(/^[a-z0-9-]*$/, 'Slug can only contain lowercase letters, numbers, and hyphens')
    .optional()
    .or(z.literal('')),
  description: z.string()
    .max(500, 'Description must be less than 500 characters')
    .optional()
    .or(z.literal('')),
  parent_id: z.number().nullable().optional(),
})

function CategoriesPage() {
  const queryClient = useQueryClient()
  const toast = useToast()
  const [search, setSearch] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [editingCategory, setEditingCategory] = useState(null)
  const [expandedCategories, setExpandedCategories] = useState(new Set())

  // Form handling with validation
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(categorySchema),
    defaultValues: {
      name: '',
      slug: '',
      description: '',
      parent_id: null,
    },
  })

  const watchName = watch('name')

  // Auto-generate slug from name
  useEffect(() => {
    if (!editingCategory && watchName) {
      const autoSlug = watchName
        .toLowerCase()
        .replace(/[^a-z0-9\s-]/g, '')
        .replace(/\s+/g, '-')
        .replace(/-+/g, '-')
        .trim()
      setValue('slug', autoSlug)
    }
  }, [watchName, editingCategory, setValue])

  // Fetch categories
  const { data: categories, isLoading, error, refetch } = useQuery({
    queryKey: ['categories', search],
    queryFn: () => categoriesApi.getAll({ search }),
    select: (res) => res.data,
  })

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data) => categoriesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries(['categories'])
      toast.success('Category created successfully')
      closeModal()
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to create category')
    },
  })

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }) => categoriesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['categories'])
      toast.success('Category updated successfully')
      closeModal()
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to update category')
    },
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id) => categoriesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries(['categories'])
      toast.success('Category deleted successfully')
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to delete category')
    },
  })

  const openCreateModal = (parentId = null) => {
    setEditingCategory(null)
    reset({
      name: '',
      slug: '',
      description: '',
      parent_id: parentId,
    })
    setShowModal(true)
  }

  const openEditModal = (category) => {
    setEditingCategory(category)
    reset({
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
    reset({
      name: '',
      slug: '',
      description: '',
      parent_id: null,
    })
  }

  const onSubmit = (data) => {
    const submitData = {
      ...data,
      slug: data.slug || data.name.toLowerCase().replace(/\s+/g, '-'),
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
          className={`flex items-center gap-3 py-3 px-4 hover:bg-gray-50 dark:hover:bg-gray-800 border-b border-gray-100 dark:border-gray-700 ${
            level > 0 ? 'bg-gray-50/50 dark:bg-gray-800/50' : ''
          }`}
          style={{ paddingLeft: `${level * 24 + 16}px` }}
        >
          {hasChildren ? (
            <button
              onClick={() => toggleExpand(category.id)}
              className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
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
            <p className="font-medium text-gray-900 dark:text-gray-100">{category.name}</p>
            <p className="text-sm text-gray-500 dark:text-gray-400 truncate">{category.slug}</p>
          </div>

          <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
            <FileText className="h-4 w-4" />
            <span>{category.content_count || 0}</span>
          </div>

          <div className="flex items-center gap-1">
            <button
              onClick={() => openCreateModal(category.id)}
              className="p-2 text-gray-600 dark:text-gray-400 hover:text-primary-600 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
              title="Add subcategory"
            >
              <Plus className="h-4 w-4" />
            </button>
            <button
              onClick={() => openEditModal(category)}
              className="p-2 text-gray-600 dark:text-gray-400 hover:text-primary-600 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
            >
              <Edit2 className="h-4 w-4" />
            </button>
            <button
              onClick={() => handleDelete(category)}
              className="p-2 text-gray-600 dark:text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg"
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

  // Error state
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <AlertCircle className="h-12 w-12 text-red-500 mb-4" />
        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">Failed to load categories</h3>
        <p className="text-gray-500 dark:text-gray-400 mt-1">{error.message}</p>
        <Button onClick={() => refetch()} className="mt-4">
          <RefreshCw className="h-4 w-4 mr-2" />
          Try Again
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Categories</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">Organize your content with categories</p>
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
              <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">No categories</h3>
              <p className="text-gray-500 dark:text-gray-400 mt-1">Create your first category to organize content.</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-100 dark:divide-gray-700">
              {categoryTree?.map((category) => renderCategory(category))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-md mx-4">
            <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {editingCategory ? 'Edit Category' : 'Create Category'}
              </h2>
              <button
                onClick={closeModal}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
              >
                <X className="h-5 w-5 text-gray-500 dark:text-gray-400" />
              </button>
            </div>
            <form onSubmit={handleSubmit(onSubmit)} className="p-6 space-y-4">
              <div>
                <Input
                  label="Name"
                  {...register('name')}
                  error={errors.name?.message}
                />
              </div>
              <div>
                <Input
                  label="Slug"
                  {...register('slug')}
                  placeholder="auto-generated-from-name"
                  error={errors.slug?.message}
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  URL-friendly identifier. Leave empty to auto-generate.
                </p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Parent Category
                </label>
                <select
                  {...register('parent_id', {
                    setValueAs: (v) => (v === '' ? null : parseInt(v)),
                  })}
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
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Description
                </label>
                <textarea
                  rows={3}
                  {...register('description')}
                  className="input"
                  placeholder="Optional description..."
                />
                {errors.description && (
                  <p className="text-sm text-red-600 dark:text-red-400 mt-1">{errors.description.message}</p>
                )}
              </div>
              <div className="flex justify-end gap-3 pt-4">
                <Button type="button" variant="secondary" onClick={closeModal}>
                  Cancel
                </Button>
                <Button
                  type="submit"
                  isLoading={createMutation.isPending || updateMutation.isPending || isSubmitting}
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
