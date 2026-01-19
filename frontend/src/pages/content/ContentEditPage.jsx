import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { contentApi, categoriesApi } from '../../services/api'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card'
import RichTextEditor from '../../components/editor/RichTextEditor'
import { ArrowLeft, Save, Trash2 } from 'lucide-react'

const contentSchema = z.object({
  title: z.string().min(1, 'Title is required'),
  slug: z.string().optional(),
  body: z.string().min(1, 'Content body is required'),
  excerpt: z.string().optional(),
  status: z.enum(['draft', 'published', 'archived']),
  category_id: z.number().optional().nullable(),
})

function ContentEditPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const isNew = !id
  const [bodyContent, setBodyContent] = useState('')

  // Fetch content if editing
  const { data: content, isLoading: contentLoading } = useQuery({
    queryKey: ['content', id],
    queryFn: () => contentApi.getById(id),
    select: (res) => res.data,
    enabled: !isNew,
  })

  // Fetch categories
  const { data: categories } = useQuery({
    queryKey: ['categories'],
    queryFn: () => categoriesApi.getAll(),
    select: (res) => res.data,
  })

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    formState: { errors, isDirty },
  } = useForm({
    resolver: zodResolver(contentSchema),
    defaultValues: {
      title: '',
      slug: '',
      body: '',
      excerpt: '',
      status: 'draft',
      category_id: null,
    },
  })

  // Reset form when content loads
  useEffect(() => {
    if (content) {
      reset({
        title: content.title || '',
        slug: content.slug || '',
        body: content.body || '',
        excerpt: content.excerpt || '',
        status: content.status || 'draft',
        category_id: content.category_id || null,
      })
      setBodyContent(content.body || '')
    }
  }, [content, reset])

  // Update form value when editor content changes
  const handleEditorChange = (html) => {
    setBodyContent(html)
    setValue('body', html, { shouldDirty: true })
  }

  // Save mutation
  const saveMutation = useMutation({
    mutationFn: (data) => (isNew ? contentApi.create(data) : contentApi.update(id, data)),
    onSuccess: (res) => {
      queryClient.invalidateQueries(['content'])
      if (isNew) {
        navigate(`/content/${res.data.id}`)
      }
    },
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: () => contentApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries(['content'])
      navigate('/content')
    },
  })

  const onSubmit = (data) => {
    saveMutation.mutate(data)
  }

  const handleDelete = () => {
    if (window.confirm('Are you sure you want to delete this content? This action cannot be undone.')) {
      deleteMutation.mutate()
    }
  }

  if (contentLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/content')}
            className="p-2 rounded-lg hover:bg-gray-100"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {isNew ? 'Create Content' : 'Edit Content'}
            </h1>
            <p className="text-gray-500 mt-1">
              {isNew ? 'Create a new article or page' : `Editing: ${content?.title}`}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {!isNew && (
            <Button variant="danger" onClick={handleDelete} disabled={deleteMutation.isPending}>
              <Trash2 className="h-4 w-4 mr-2" />
              Delete
            </Button>
          )}
          <Button
            onClick={handleSubmit(onSubmit)}
            isLoading={saveMutation.isPending}
            disabled={!isDirty && !isNew}
          >
            <Save className="h-4 w-4 mr-2" />
            {isNew ? 'Create' : 'Save'}
          </Button>
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main content area */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Content Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <Input
                label="Title"
                placeholder="Enter content title"
                error={errors.title?.message}
                {...register('title')}
              />

              <Input
                label="Slug"
                placeholder="url-friendly-slug (auto-generated if empty)"
                error={errors.slug?.message}
                {...register('slug')}
              />

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Content Body
                </label>
                <RichTextEditor
                  content={bodyContent}
                  onChange={handleEditorChange}
                  placeholder="Write your content here..."
                />
                {errors.body && (
                  <p className="mt-1 text-sm text-red-600">{errors.body.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Excerpt
                </label>
                <textarea
                  rows={3}
                  placeholder="Brief summary of the content..."
                  className="input"
                  {...register('excerpt')}
                />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Publish</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Status
                </label>
                <select className="input" {...register('status')}>
                  <option value="draft">Draft</option>
                  <option value="published">Published</option>
                  <option value="archived">Archived</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Category
                </label>
                <select
                  className="input"
                  {...register('category_id', { valueAsNumber: true })}
                >
                  <option value="">No category</option>
                  {categories?.map((cat) => (
                    <option key={cat.id} value={cat.id}>
                      {cat.name}
                    </option>
                  ))}
                </select>
              </div>
            </CardContent>
          </Card>

          {!isNew && content && (
            <Card>
              <CardHeader>
                <CardTitle>Info</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-gray-500 space-y-2">
                <div className="flex justify-between">
                  <span>Created</span>
                  <span>{new Date(content.created_at).toLocaleDateString()}</span>
                </div>
                <div className="flex justify-between">
                  <span>Updated</span>
                  <span>{new Date(content.updated_at).toLocaleDateString()}</span>
                </div>
                <div className="flex justify-between">
                  <span>Author</span>
                  <span>{content.author?.username || 'Unknown'}</span>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </form>
    </div>
  )
}

export default ContentEditPage
