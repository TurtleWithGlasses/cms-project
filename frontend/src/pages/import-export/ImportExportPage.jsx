import { useState, useRef } from 'react'
import { useMutation } from '@tanstack/react-query'
import { importExportApi } from '../../services/api'
import { useToast } from '../../components/ui/Toast'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card'
import Button from '../../components/ui/Button'
import {
  Upload,
  Download,
  FileJson,
  FileSpreadsheet,
  FileText,
  CheckCircle,
  AlertCircle,
  Loader2,
  FolderOpen,
  ArrowRight,
  X,
} from 'lucide-react'

const exportFormats = [
  { id: 'json', name: 'JSON', icon: FileJson, description: 'Full data export with relationships' },
  { id: 'csv', name: 'CSV', icon: FileSpreadsheet, description: 'Spreadsheet compatible format' },
  { id: 'xml', name: 'XML', icon: FileText, description: 'Standard XML format' },
]

const dataTypes = [
  { id: 'content', name: 'Content', description: 'All posts, pages, and articles' },
  { id: 'categories', name: 'Categories', description: 'Category hierarchy and metadata' },
  { id: 'tags', name: 'Tags', description: 'All tags and associations' },
  { id: 'users', name: 'Users', description: 'User accounts (excluding passwords)' },
  { id: 'media', name: 'Media', description: 'Media library metadata' },
  { id: 'comments', name: 'Comments', description: 'All comments and replies' },
  { id: 'settings', name: 'Settings', description: 'System configuration' },
]

function ImportExportPage() {
  const toast = useToast()
  const fileInputRef = useRef(null)
  const [activeTab, setActiveTab] = useState('export')

  // Export state
  const [exportFormat, setExportFormat] = useState('json')
  const [selectedDataTypes, setSelectedDataTypes] = useState(['content'])
  const [includeMedia, setIncludeMedia] = useState(false)

  // Import state
  const [importFile, setImportFile] = useState(null)
  const [importPreview, setImportPreview] = useState(null)
  const [importOptions, setImportOptions] = useState({
    overwriteExisting: false,
    skipDuplicates: true,
    importMedia: true,
  })

  // Export mutation
  const exportMutation = useMutation({
    mutationFn: () => importExportApi.export({
      format: exportFormat,
      dataTypes: selectedDataTypes,
      includeMedia,
    }),
    onSuccess: (response) => {
      // Create download link
      const blob = new Blob([response.data], {
        type: exportFormat === 'json' ? 'application/json' :
              exportFormat === 'csv' ? 'text/csv' : 'application/xml'
      })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `cms-export-${new Date().toISOString().split('T')[0]}.${exportFormat}`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      toast.success('Export completed successfully')
    },
    onError: () => toast.error('Export failed. Please try again.'),
  })

  // Import mutation
  const importMutation = useMutation({
    mutationFn: (formData) => importExportApi.import(formData),
    onSuccess: (response) => {
      toast.success(`Import completed: ${response.data.imported} items imported`)
      setImportFile(null)
      setImportPreview(null)
    },
    onError: (error) => toast.error(error.response?.data?.message || 'Import failed'),
  })

  // Preview mutation
  const previewMutation = useMutation({
    mutationFn: (formData) => importExportApi.preview(formData),
    onSuccess: (response) => {
      setImportPreview(response.data)
    },
    onError: () => toast.error('Failed to preview file'),
  })

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0]
    if (file) {
      setImportFile(file)
      const formData = new FormData()
      formData.append('file', file)
      previewMutation.mutate(formData)
    }
  }

  const handleExport = () => {
    if (selectedDataTypes.length === 0) {
      toast.warning('Please select at least one data type to export')
      return
    }
    exportMutation.mutate()
  }

  const handleImport = () => {
    if (!importFile) return
    const formData = new FormData()
    formData.append('file', importFile)
    formData.append('options', JSON.stringify(importOptions))
    importMutation.mutate(formData)
  }

  const toggleDataType = (id) => {
    setSelectedDataTypes((prev) =>
      prev.includes(id) ? prev.filter((t) => t !== id) : [...prev, id]
    )
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Import & Export</h1>
        <p className="text-gray-500 mt-1">Transfer your content and settings</p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200">
        <button
          onClick={() => setActiveTab('export')}
          className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'export'
              ? 'border-primary-600 text-primary-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <Download className="h-4 w-4 inline-block mr-2" />
          Export Data
        </button>
        <button
          onClick={() => setActiveTab('import')}
          className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'import'
              ? 'border-primary-600 text-primary-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <Upload className="h-4 w-4 inline-block mr-2" />
          Import Data
        </button>
      </div>

      {/* Export Tab */}
      {activeTab === 'export' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Export format selection */}
          <Card>
            <CardHeader>
              <CardTitle>Export Format</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {exportFormats.map((format) => {
                const FormatIcon = format.icon
                return (
                  <label
                    key={format.id}
                    className={`flex items-center gap-4 p-4 rounded-lg border-2 cursor-pointer transition-colors ${
                      exportFormat === format.id
                        ? 'border-primary-500 bg-primary-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <input
                      type="radio"
                      name="exportFormat"
                      value={format.id}
                      checked={exportFormat === format.id}
                      onChange={() => setExportFormat(format.id)}
                      className="sr-only"
                    />
                    <FormatIcon className={`h-8 w-8 ${
                      exportFormat === format.id ? 'text-primary-600' : 'text-gray-400'
                    }`} />
                    <div className="flex-1">
                      <p className="font-medium text-gray-900">{format.name}</p>
                      <p className="text-sm text-gray-500">{format.description}</p>
                    </div>
                    {exportFormat === format.id && (
                      <CheckCircle className="h-5 w-5 text-primary-600" />
                    )}
                  </label>
                )
              })}
            </CardContent>
          </Card>

          {/* Data type selection */}
          <Card>
            <CardHeader>
              <CardTitle>Data to Export</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {dataTypes.map((type) => (
                  <label
                    key={type.id}
                    className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selectedDataTypes.includes(type.id)}
                      onChange={() => toggleDataType(type.id)}
                      className="h-4 w-4 text-primary-600 rounded border-gray-300 focus:ring-primary-500"
                    />
                    <div className="flex-1">
                      <p className="font-medium text-gray-900">{type.name}</p>
                      <p className="text-sm text-gray-500">{type.description}</p>
                    </div>
                  </label>
                ))}
              </div>

              <div className="mt-4 pt-4 border-t border-gray-200">
                <label className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={includeMedia}
                    onChange={(e) => setIncludeMedia(e.target.checked)}
                    className="h-4 w-4 text-primary-600 rounded border-gray-300 focus:ring-primary-500"
                  />
                  <div className="flex-1">
                    <p className="font-medium text-gray-900">Include Media Files</p>
                    <p className="text-sm text-gray-500">Export will include actual media files (larger file size)</p>
                  </div>
                </label>
              </div>

              <div className="mt-6">
                <Button
                  onClick={handleExport}
                  disabled={exportMutation.isPending || selectedDataTypes.length === 0}
                  className="w-full"
                >
                  {exportMutation.isPending ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Exporting...
                    </>
                  ) : (
                    <>
                      <Download className="h-4 w-4 mr-2" />
                      Export Selected Data
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Import Tab */}
      {activeTab === 'import' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* File upload */}
          <Card>
            <CardHeader>
              <CardTitle>Upload File</CardTitle>
            </CardHeader>
            <CardContent>
              <input
                ref={fileInputRef}
                type="file"
                accept=".json,.csv,.xml"
                onChange={handleFileSelect}
                className="hidden"
              />

              {!importFile ? (
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="w-full border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-primary-500 hover:bg-primary-50 transition-colors"
                >
                  <FolderOpen className="h-12 w-12 mx-auto text-gray-400 mb-4" />
                  <p className="font-medium text-gray-900">Click to select a file</p>
                  <p className="text-sm text-gray-500 mt-1">
                    Supports JSON, CSV, and XML formats
                  </p>
                </button>
              ) : (
                <div className="border border-gray-200 rounded-lg p-4">
                  <div className="flex items-center gap-4">
                    <FileJson className="h-10 w-10 text-primary-600" />
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-gray-900 truncate">{importFile.name}</p>
                      <p className="text-sm text-gray-500">
                        {(importFile.size / 1024).toFixed(2)} KB
                      </p>
                    </div>
                    <button
                      onClick={() => {
                        setImportFile(null)
                        setImportPreview(null)
                      }}
                      className="p-2 hover:bg-gray-100 rounded-lg"
                    >
                      <X className="h-5 w-5 text-gray-400" />
                    </button>
                  </div>
                </div>
              )}

              {/* Import options */}
              <div className="mt-6 space-y-3">
                <h4 className="font-medium text-gray-900">Import Options</h4>
                <label className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={importOptions.overwriteExisting}
                    onChange={(e) => setImportOptions({ ...importOptions, overwriteExisting: e.target.checked })}
                    className="h-4 w-4 text-primary-600 rounded border-gray-300 focus:ring-primary-500"
                  />
                  <div>
                    <p className="font-medium text-gray-900">Overwrite Existing</p>
                    <p className="text-sm text-gray-500">Replace existing items with imported data</p>
                  </div>
                </label>
                <label className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={importOptions.skipDuplicates}
                    onChange={(e) => setImportOptions({ ...importOptions, skipDuplicates: e.target.checked })}
                    className="h-4 w-4 text-primary-600 rounded border-gray-300 focus:ring-primary-500"
                  />
                  <div>
                    <p className="font-medium text-gray-900">Skip Duplicates</p>
                    <p className="text-sm text-gray-500">Skip items that already exist</p>
                  </div>
                </label>
                <label className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={importOptions.importMedia}
                    onChange={(e) => setImportOptions({ ...importOptions, importMedia: e.target.checked })}
                    className="h-4 w-4 text-primary-600 rounded border-gray-300 focus:ring-primary-500"
                  />
                  <div>
                    <p className="font-medium text-gray-900">Import Media Files</p>
                    <p className="text-sm text-gray-500">Import associated media files if included</p>
                  </div>
                </label>
              </div>
            </CardContent>
          </Card>

          {/* Import preview */}
          <Card>
            <CardHeader>
              <CardTitle>Import Preview</CardTitle>
            </CardHeader>
            <CardContent>
              {previewMutation.isPending ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
                </div>
              ) : importPreview ? (
                <div className="space-y-4">
                  <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                    <div className="flex items-center gap-2 text-green-700">
                      <CheckCircle className="h-5 w-5" />
                      <span className="font-medium">File validated successfully</span>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <h4 className="font-medium text-gray-900">Items to Import</h4>
                    {Object.entries(importPreview.summary || {}).map(([type, count]) => (
                      <div key={type} className="flex items-center justify-between py-2 border-b border-gray-100">
                        <span className="text-gray-700 capitalize">{type}</span>
                        <span className="font-medium text-gray-900">{count} items</span>
                      </div>
                    ))}
                  </div>

                  {importPreview.warnings?.length > 0 && (
                    <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                      <div className="flex items-center gap-2 text-yellow-700 mb-2">
                        <AlertCircle className="h-5 w-5" />
                        <span className="font-medium">Warnings</span>
                      </div>
                      <ul className="text-sm text-yellow-600 space-y-1">
                        {importPreview.warnings.map((warning, i) => (
                          <li key={i}>{warning}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <Button
                    onClick={handleImport}
                    disabled={importMutation.isPending}
                    className="w-full"
                  >
                    {importMutation.isPending ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Importing...
                      </>
                    ) : (
                      <>
                        <ArrowRight className="h-4 w-4 mr-2" />
                        Start Import
                      </>
                    )}
                  </Button>
                </div>
              ) : (
                <div className="text-center py-12 text-gray-500">
                  <Upload className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                  <p>Upload a file to see import preview</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}

export default ImportExportPage
