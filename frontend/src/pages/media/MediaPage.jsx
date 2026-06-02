import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { mediaApi } from '../../services/api'
import Button from '../../components/ui/Button'
import { Card, CardContent } from '../../components/ui/Card'
import { useToast } from '../../components/ui/Toast'
import { SkeletonMediaGrid, SkeletonTable } from '../../components/ui/Skeleton'
import {
  Upload,
  Image,
  File,
  Film,
  Music,
  Trash2,
  Download,
  Copy,
  Search,
  Grid,
  List,
  X,
  CheckCircle,
  AlertCircle,
  RefreshCw,
} from 'lucide-react'

function MediaPage() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const fileInputRef = useRef(null)
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [viewMode, setViewMode] = useState('grid')
  const [selectedMedia, setSelectedMedia] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)

  // Fetch media
  const { data: media, isLoading, error, refetch } = useQuery({
    queryKey: ['media', search, typeFilter],
    queryFn: () => mediaApi.getAll({ search, type: typeFilter }),
    select: (res) => res.data?.media ?? res.data ?? [],
  })

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: async (files) => {
      setUploading(true)
      setUploadProgress(0)
      const results = []
      for (let i = 0; i < files.length; i++) {
        const formData = new FormData()
        formData.append('file', files[i])
        const result = await mediaApi.upload(formData)
        results.push(result.data)
        setUploadProgress(((i + 1) / files.length) * 100)
      }
      return results
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries(['media'])
      setUploading(false)
      setUploadProgress(0)
      toast({
        title: 'Upload complete',
        description: `Successfully uploaded ${data.length} file(s).`,
        variant: 'success',
      })
    },
    onError: (error) => {
      setUploading(false)
      setUploadProgress(0)
      toast({
        title: 'Upload failed',
        description: error.response?.data?.detail || error.message || 'An error occurred while uploading files.',
        variant: 'error',
      })
    },
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id) => mediaApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries(['media'])
      setSelectedMedia(null)
      toast({
        title: 'File deleted',
        description: 'The file has been deleted successfully.',
        variant: 'success',
      })
    },
    onError: (error) => {
      toast({
        title: 'Failed to delete',
        description: error.response?.data?.detail || error.message || 'An error occurred while deleting the file.',
        variant: 'error',
      })
    },
  })

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files)
    if (files.length > 0) {
      uploadMutation.mutate(files)
    }
    e.target.value = ''
  }

  const handleDrop = (e) => {
    e.preventDefault()
    const files = Array.from(e.dataTransfer.files)
    if (files.length > 0) {
      uploadMutation.mutate(files)
    }
  }

  const handleDragOver = (e) => {
    e.preventDefault()
  }

  const handleDelete = (item) => {
    if (window.confirm(`Delete "${item.filename}"?`)) {
      deleteMutation.mutate(item.id)
    }
  }

  const copyUrl = (url) => {
    navigator.clipboard.writeText(url)
    toast({
      title: 'URL copied',
      description: 'The file URL has been copied to clipboard.',
      variant: 'success',
    })
  }

  const getFileIcon = (mimeType) => {
    if (mimeType?.startsWith('image/')) return Image
    if (mimeType?.startsWith('video/')) return Film
    if (mimeType?.startsWith('audio/')) return Music
    return File
  }

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  const isImage = (mimeType) => mimeType?.startsWith('image/')

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Media Library</h1>
            <p className="text-gray-500 dark:text-gray-400 mt-1">Upload and manage your media files</p>
          </div>
        </div>
        <div className="flex flex-col items-center justify-center py-16 space-y-4">
          <AlertCircle className="h-12 w-12 text-red-500" />
          <div className="text-center">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Failed to load media</h2>
            <p className="text-gray-600 dark:text-gray-400 mt-1">
              {error.response?.data?.detail || error.message || 'An error occurred while loading media files.'}
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
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Media Library</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">Upload and manage your media files</p>
        </div>
        <Button onClick={() => fileInputRef.current?.click()} disabled={uploading}>
          <Upload className="h-4 w-4 mr-2" />
          Upload Files
        </Button>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          onChange={handleFileSelect}
          className="hidden"
          accept="image/*,video/*,audio/*,.pdf,.doc,.docx"
        />
      </div>

      {/* Upload progress */}
      {uploading && (
        <Card>
          <CardContent className="py-4">
            <div className="flex items-center gap-4">
              <div className="flex-1">
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-700 dark:text-gray-300">Uploading...</span>
                  <span className="text-gray-700 dark:text-gray-300">{Math.round(uploadProgress)}%</span>
                </div>
                <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary-600 transition-all duration-300"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search files..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="input pl-10 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                />
              </div>
            </div>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="input w-full sm:w-40 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
            >
              <option value="">All Types</option>
              <option value="image">Images</option>
              <option value="video">Videos</option>
              <option value="audio">Audio</option>
              <option value="document">Documents</option>
            </select>
            <div className="flex border border-gray-300 dark:border-gray-600 rounded-lg overflow-hidden">
              <button
                onClick={() => setViewMode('grid')}
                className={`p-2 ${viewMode === 'grid' ? 'bg-primary-100 text-primary-600 dark:bg-primary-900/50 dark:text-primary-400' : 'hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-400'}`}
              >
                <Grid className="h-5 w-5" />
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={`p-2 ${viewMode === 'list' ? 'bg-primary-100 text-primary-600 dark:bg-primary-900/50 dark:text-primary-400' : 'hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-400'}`}
              >
                <List className="h-5 w-5" />
              </button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Drop zone */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        className="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-8 text-center hover:border-primary-500 dark:hover:border-primary-400 transition-colors"
      >
        <Upload className="h-10 w-10 text-gray-400 mx-auto mb-4" />
        <p className="text-gray-600 dark:text-gray-400">
          Drag and drop files here, or{' '}
          <button
            onClick={() => fileInputRef.current?.click()}
            className="text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300 font-medium"
          >
            browse
          </button>
        </p>
        <p className="text-sm text-gray-500 dark:text-gray-500 mt-1">
          Supports images, videos, audio, and documents
        </p>
      </div>

      {/* Media grid/list */}
      {isLoading ? (
        viewMode === 'grid' ? (
          <SkeletonMediaGrid items={10} />
        ) : (
          <Card>
            <CardContent className="p-0">
              <SkeletonTable rows={5} columns={5} />
            </CardContent>
          </Card>
        )
      ) : media?.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Image className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">No media files</h3>
            <p className="text-gray-500 dark:text-gray-400 mt-1">Upload your first file to get started.</p>
          </CardContent>
        </Card>
      ) : viewMode === 'grid' ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {media?.map((item) => {
            const FileIcon = getFileIcon(item.mime_type)
            return (
              <div
                key={item.id}
                onClick={() => setSelectedMedia(item)}
                className="group relative aspect-square bg-gray-100 dark:bg-gray-700 rounded-lg overflow-hidden cursor-pointer hover:ring-2 hover:ring-primary-500"
              >
                {isImage(item.mime_type) ? (
                  <img
                    src={item.url}
                    alt={item.filename}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <FileIcon className="h-12 w-12 text-gray-400" />
                  </div>
                )}
                <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-40 transition-all flex items-center justify-center opacity-0 group-hover:opacity-100">
                  <CheckCircle className="h-8 w-8 text-white" />
                </div>
                <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent p-2">
                  <p className="text-white text-xs truncate">{item.filename}</p>
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        <Card>
          <CardContent className="p-0">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                    File
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                    Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                    Size
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                    Uploaded
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {media?.map((item) => {
                  const FileIcon = getFileIcon(item.mime_type)
                  return (
                    <tr
                      key={item.id}
                      className="hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer transition-colors"
                      onClick={() => setSelectedMedia(item)}
                    >
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          {isImage(item.mime_type) ? (
                            <img
                              src={item.url}
                              alt={item.filename}
                              className="h-10 w-10 rounded object-cover"
                            />
                          ) : (
                            <div className="h-10 w-10 bg-gray-100 dark:bg-gray-700 rounded flex items-center justify-center">
                              <FileIcon className="h-5 w-5 text-gray-400" />
                            </div>
                          )}
                          <span className="text-sm font-medium text-gray-900 dark:text-white truncate max-w-xs">
                            {item.filename}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                        {item.mime_type}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                        {formatFileSize(item.size)}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                        {new Date(item.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            handleDelete(item)
                          }}
                          disabled={deleteMutation.isPending}
                          className="p-2 text-gray-600 dark:text-gray-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg disabled:opacity-50"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}

      {/* Media detail modal */}
      {selectedMedia && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
            <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white truncate">{selectedMedia.filename}</h2>
              <button
                onClick={() => setSelectedMedia(null)}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg text-gray-500 dark:text-gray-400"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="flex-1 overflow-auto p-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Preview */}
                <div className="bg-gray-100 dark:bg-gray-700 rounded-lg overflow-hidden flex items-center justify-center min-h-[200px]">
                  {isImage(selectedMedia.mime_type) ? (
                    <img
                      src={selectedMedia.url}
                      alt={selectedMedia.filename}
                      className="max-w-full max-h-[400px] object-contain"
                    />
                  ) : (
                    <div className="text-center p-8">
                      {(() => {
                        const FileIcon = getFileIcon(selectedMedia.mime_type)
                        return <FileIcon className="h-16 w-16 text-gray-400 mx-auto mb-4" />
                      })()}
                      <p className="text-gray-500 dark:text-gray-400">Preview not available</p>
                    </div>
                  )}
                </div>

                {/* Details */}
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
                      File URL
                    </label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        readOnly
                        value={selectedMedia.url}
                        className="input flex-1 text-sm dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                      />
                      <Button
                        variant="secondary"
                        onClick={() => copyUrl(selectedMedia.url)}
                      >
                        <Copy className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
                        Type
                      </label>
                      <p className="text-sm text-gray-900 dark:text-white">{selectedMedia.mime_type}</p>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
                        Size
                      </label>
                      <p className="text-sm text-gray-900 dark:text-white">
                        {formatFileSize(selectedMedia.size)}
                      </p>
                    </div>
                    {selectedMedia.width && selectedMedia.height && (
                      <div>
                        <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
                          Dimensions
                        </label>
                        <p className="text-sm text-gray-900 dark:text-white">
                          {selectedMedia.width} × {selectedMedia.height}
                        </p>
                      </div>
                    )}
                    <div>
                      <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
                        Uploaded
                      </label>
                      <p className="text-sm text-gray-900 dark:text-white">
                        {new Date(selectedMedia.created_at).toLocaleString()}
                      </p>
                    </div>
                  </div>

                  <div className="flex gap-2 pt-4">
                    <a
                      href={selectedMedia.url}
                      download
                      className="btn btn-secondary flex items-center gap-2"
                    >
                      <Download className="h-4 w-4" />
                      Download
                    </a>
                    <Button
                      variant="danger"
                      onClick={() => handleDelete(selectedMedia)}
                      disabled={deleteMutation.isPending}
                    >
                      <Trash2 className="h-4 w-4 mr-2" />
                      Delete
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default MediaPage
