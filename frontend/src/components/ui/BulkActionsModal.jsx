import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import Button from './Button'
import {
  X,
  Trash2,
  Archive,
  Tag,
  FolderOpen,
  Send,
  Eye,
  EyeOff,
  AlertTriangle,
  CheckCircle,
  Loader2,
} from 'lucide-react'

const defaultActions = [
  {
    id: 'publish',
    label: 'Publish',
    icon: Send,
    color: 'text-green-600',
    description: 'Make selected items publicly visible',
  },
  {
    id: 'unpublish',
    label: 'Unpublish',
    icon: EyeOff,
    color: 'text-yellow-600',
    description: 'Hide selected items from public view',
  },
  {
    id: 'archive',
    label: 'Archive',
    icon: Archive,
    color: 'text-blue-600',
    description: 'Move selected items to archive',
  },
  {
    id: 'delete',
    label: 'Delete',
    icon: Trash2,
    color: 'text-red-600',
    description: 'Permanently delete selected items',
    dangerous: true,
  },
]

function BulkActionsModal({
  isOpen,
  onClose,
  selectedItems = [],
  itemType = 'items',
  actions = defaultActions,
  onAction,
}) {
  const [selectedAction, setSelectedAction] = useState(null)
  const [confirmText, setConfirmText] = useState('')
  const [result, setResult] = useState(null)

  const actionMutation = useMutation({
    mutationFn: ({ action, items }) => onAction(action, items),
    onSuccess: (data) => {
      setResult({
        success: true,
        message: data?.message || `Successfully processed ${selectedItems.length} ${itemType}`,
      })
    },
    onError: (error) => {
      setResult({
        success: false,
        message: error?.message || `Failed to process ${itemType}`,
      })
    },
  })

  const handleAction = () => {
    if (!selectedAction) return

    // For dangerous actions, require confirmation
    if (selectedAction.dangerous && confirmText !== 'DELETE') {
      return
    }

    actionMutation.mutate({
      action: selectedAction.id,
      items: selectedItems,
    })
  }

  const handleClose = () => {
    setSelectedAction(null)
    setConfirmText('')
    setResult(null)
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="min-h-screen px-4 text-center">
        {/* Backdrop */}
        <div
          className="fixed inset-0 bg-black/50 transition-opacity"
          onClick={handleClose}
        />

        {/* Modal */}
        <div className="inline-block w-full max-w-lg my-8 text-left align-middle bg-white rounded-xl shadow-xl transform transition-all">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Bulk Actions</h3>
              <p className="text-sm text-gray-500">
                {selectedItems.length} {itemType} selected
              </p>
            </div>
            <button
              onClick={handleClose}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <X className="h-5 w-5 text-gray-400" />
            </button>
          </div>

          {/* Content */}
          <div className="px-6 py-4">
            {result ? (
              /* Result state */
              <div className="text-center py-6">
                {result.success ? (
                  <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-4" />
                ) : (
                  <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
                )}
                <p className={`font-medium ${result.success ? 'text-green-700' : 'text-red-700'}`}>
                  {result.message}
                </p>
                <Button onClick={handleClose} className="mt-4">
                  Close
                </Button>
              </div>
            ) : actionMutation.isPending ? (
              /* Loading state */
              <div className="text-center py-8">
                <Loader2 className="h-8 w-8 animate-spin text-primary-600 mx-auto mb-4" />
                <p className="text-gray-600">Processing {selectedItems.length} {itemType}...</p>
              </div>
            ) : selectedAction ? (
              /* Confirmation state */
              <div className="space-y-4">
                <div className={`p-4 rounded-lg ${selectedAction.dangerous ? 'bg-red-50' : 'bg-gray-50'}`}>
                  <div className="flex items-center gap-3">
                    <selectedAction.icon className={`h-6 w-6 ${selectedAction.color}`} />
                    <div>
                      <p className="font-medium text-gray-900">{selectedAction.label}</p>
                      <p className="text-sm text-gray-500">{selectedAction.description}</p>
                    </div>
                  </div>
                </div>

                <p className="text-gray-700">
                  You are about to <strong>{selectedAction.label.toLowerCase()}</strong>{' '}
                  {selectedItems.length} {itemType}. This action
                  {selectedAction.dangerous ? ' cannot be undone.' : ' can be reversed.'}
                </p>

                {selectedAction.dangerous && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Type "DELETE" to confirm
                    </label>
                    <input
                      type="text"
                      value={confirmText}
                      onChange={(e) => setConfirmText(e.target.value)}
                      placeholder="DELETE"
                      className="input"
                    />
                  </div>
                )}

                <div className="flex justify-end gap-3 pt-4">
                  <Button variant="outline" onClick={() => setSelectedAction(null)}>
                    Back
                  </Button>
                  <Button
                    onClick={handleAction}
                    disabled={selectedAction.dangerous && confirmText !== 'DELETE'}
                    className={selectedAction.dangerous ? 'bg-red-600 hover:bg-red-700' : ''}
                  >
                    {selectedAction.label} {selectedItems.length} {itemType}
                  </Button>
                </div>
              </div>
            ) : (
              /* Action selection state */
              <div className="space-y-2">
                {actions.map((action) => {
                  const Icon = action.icon
                  return (
                    <button
                      key={action.id}
                      onClick={() => setSelectedAction(action)}
                      className="w-full flex items-center gap-4 p-4 rounded-lg border border-gray-200 hover:border-gray-300 hover:bg-gray-50 transition-colors text-left"
                    >
                      <div className={`h-10 w-10 rounded-lg flex items-center justify-center ${
                        action.dangerous ? 'bg-red-100' : 'bg-gray-100'
                      }`}>
                        <Icon className={`h-5 w-5 ${action.color}`} />
                      </div>
                      <div className="flex-1">
                        <p className="font-medium text-gray-900">{action.label}</p>
                        <p className="text-sm text-gray-500">{action.description}</p>
                      </div>
                    </button>
                  )
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

// Bulk selection bar component
export function BulkSelectionBar({ selectedCount, onClear, onBulkAction, itemType = 'items' }) {
  if (selectedCount === 0) return null

  return (
    <div className="fixed bottom-6 left-1/2 transform -translate-x-1/2 z-40">
      <div className="bg-gray-900 text-white rounded-lg shadow-lg px-6 py-3 flex items-center gap-4">
        <span className="text-sm">
          <strong>{selectedCount}</strong> {itemType} selected
        </span>
        <div className="h-4 w-px bg-gray-700" />
        <button
          onClick={onBulkAction}
          className="text-sm font-medium hover:text-primary-300 transition-colors"
        >
          Bulk Actions
        </button>
        <button
          onClick={onClear}
          className="text-sm text-gray-400 hover:text-white transition-colors"
        >
          Clear selection
        </button>
      </div>
    </div>
  )
}

export default BulkActionsModal
