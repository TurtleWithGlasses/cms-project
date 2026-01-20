import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Database,
  Download,
  Upload,
  Clock,
  HardDrive,
  Trash2,
  RefreshCw,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Play,
  Calendar,
  FileArchive,
  Shield,
  Settings,
} from 'lucide-react'
import { useToast } from '../../components/ui/Toast'

// Mock Backup API
const backupApi = {
  getBackups: () => Promise.resolve([
    {
      id: 1,
      name: 'Full Backup',
      type: 'full',
      status: 'completed',
      size: '245.8 MB',
      createdAt: '2024-01-15T10:30:00Z',
      includes: ['database', 'media', 'config'],
    },
    {
      id: 2,
      name: 'Database Backup',
      type: 'database',
      status: 'completed',
      size: '12.4 MB',
      createdAt: '2024-01-14T08:00:00Z',
      includes: ['database'],
    },
    {
      id: 3,
      name: 'Scheduled Backup',
      type: 'full',
      status: 'completed',
      size: '243.2 MB',
      createdAt: '2024-01-13T03:00:00Z',
      includes: ['database', 'media', 'config'],
    },
    {
      id: 4,
      name: 'Media Backup',
      type: 'media',
      status: 'failed',
      size: null,
      createdAt: '2024-01-12T15:45:00Z',
      includes: ['media'],
      error: 'Insufficient storage space',
    },
    {
      id: 5,
      name: 'Pre-update Backup',
      type: 'full',
      status: 'completed',
      size: '240.1 MB',
      createdAt: '2024-01-10T09:15:00Z',
      includes: ['database', 'media', 'config'],
    },
  ]),
  getSchedule: () => Promise.resolve({
    enabled: true,
    frequency: 'daily',
    time: '03:00',
    retention: 7,
    includeMedia: true,
    lastRun: '2024-01-15T03:00:00Z',
    nextRun: '2024-01-16T03:00:00Z',
  }),
  getStorageInfo: () => Promise.resolve({
    used: 1.2,
    total: 10,
    backupsCount: 5,
    oldestBackup: '2024-01-10T09:15:00Z',
  }),
  createBackup: (options) => Promise.resolve({ id: 6, status: 'in_progress' }),
  deleteBackup: (id) => Promise.resolve({ success: true }),
  downloadBackup: (id) => Promise.resolve(new Blob(['backup data'], { type: 'application/zip' })),
  restoreBackup: (id) => Promise.resolve({ success: true }),
  updateSchedule: (schedule) => Promise.resolve(schedule),
}

function BackupRestorePage() {
  const [showCreateBackup, setShowCreateBackup] = useState(false)
  const [showRestoreConfirm, setShowRestoreConfirm] = useState(null)
  const [showScheduleSettings, setShowScheduleSettings] = useState(false)
  const [backupOptions, setBackupOptions] = useState({
    name: '',
    includeDatabase: true,
    includeMedia: true,
    includeConfig: true,
  })

  const { toast } = useToast()
  const queryClient = useQueryClient()

  const { data: backups, isLoading: loadingBackups } = useQuery({
    queryKey: ['backups'],
    queryFn: backupApi.getBackups,
  })

  const { data: schedule } = useQuery({
    queryKey: ['backup-schedule'],
    queryFn: backupApi.getSchedule,
  })

  const { data: storage } = useQuery({
    queryKey: ['backup-storage'],
    queryFn: backupApi.getStorageInfo,
  })

  const createBackupMutation = useMutation({
    mutationFn: backupApi.createBackup,
    onSuccess: () => {
      queryClient.invalidateQueries(['backups'])
      setShowCreateBackup(false)
      setBackupOptions({ name: '', includeDatabase: true, includeMedia: true, includeConfig: true })
      toast({ title: 'Backup started', description: 'Your backup is being created.', variant: 'success' })
    },
  })

  const deleteBackupMutation = useMutation({
    mutationFn: backupApi.deleteBackup,
    onSuccess: () => {
      queryClient.invalidateQueries(['backups'])
      toast({ title: 'Backup deleted', variant: 'success' })
    },
  })

  const restoreBackupMutation = useMutation({
    mutationFn: backupApi.restoreBackup,
    onSuccess: () => {
      setShowRestoreConfirm(null)
      toast({ title: 'Restore started', description: 'Your site is being restored from backup.', variant: 'success' })
    },
  })

  const updateScheduleMutation = useMutation({
    mutationFn: backupApi.updateSchedule,
    onSuccess: () => {
      queryClient.invalidateQueries(['backup-schedule'])
      setShowScheduleSettings(false)
      toast({ title: 'Schedule updated', variant: 'success' })
    },
  })

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-500" />
      case 'in_progress':
        return <RefreshCw className="h-5 w-5 text-blue-500 animate-spin" />
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-500" />
      default:
        return null
    }
  }

  const getTypeIcon = (type) => {
    switch (type) {
      case 'full':
        return <FileArchive className="h-5 w-5 text-primary-600" />
      case 'database':
        return <Database className="h-5 w-5 text-blue-600" />
      case 'media':
        return <HardDrive className="h-5 w-5 text-purple-600" />
      default:
        return <FileArchive className="h-5 w-5 text-gray-600" />
    }
  }

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  if (loadingBackups) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  const storagePercentage = storage ? (storage.used / storage.total) * 100 : 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Backup & Restore</h1>
          <p className="text-gray-600 mt-1">Manage your site backups and restore points</p>
        </div>
        <button
          onClick={() => setShowCreateBackup(true)}
          className="btn btn-primary"
        >
          <Database className="h-4 w-4 mr-2" />
          Create Backup
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Storage Usage */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="h-10 w-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <HardDrive className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Storage Used</p>
              <p className="text-xl font-semibold text-gray-900">
                {storage?.used} GB <span className="text-sm font-normal text-gray-500">/ {storage?.total} GB</span>
              </p>
            </div>
          </div>
          <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full ${
                storagePercentage > 80 ? 'bg-red-500' : storagePercentage > 60 ? 'bg-amber-500' : 'bg-blue-500'
              }`}
              style={{ width: `${storagePercentage}%` }}
            />
          </div>
        </div>

        {/* Backup Count */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 bg-green-100 rounded-lg flex items-center justify-center">
              <FileArchive className="h-5 w-5 text-green-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Total Backups</p>
              <p className="text-xl font-semibold text-gray-900">{storage?.backupsCount}</p>
            </div>
          </div>
          <p className="text-sm text-gray-500 mt-2">
            Oldest: {storage?.oldestBackup ? formatDate(storage.oldestBackup) : 'N/A'}
          </p>
        </div>

        {/* Schedule Status */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`h-10 w-10 rounded-lg flex items-center justify-center ${
                schedule?.enabled ? 'bg-primary-100' : 'bg-gray-100'
              }`}>
                <Clock className={`h-5 w-5 ${schedule?.enabled ? 'text-primary-600' : 'text-gray-400'}`} />
              </div>
              <div>
                <p className="text-sm text-gray-500">Auto Backup</p>
                <p className="text-xl font-semibold text-gray-900">
                  {schedule?.enabled ? `Every ${schedule.frequency}` : 'Disabled'}
                </p>
              </div>
            </div>
            <button
              onClick={() => setShowScheduleSettings(true)}
              className="p-2 hover:bg-gray-100 rounded-lg"
            >
              <Settings className="h-5 w-5 text-gray-400" />
            </button>
          </div>
          {schedule?.enabled && schedule?.nextRun && (
            <p className="text-sm text-gray-500 mt-2">
              Next: {formatDate(schedule.nextRun)}
            </p>
          )}
        </div>
      </div>

      {/* Backups List */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200">
        <div className="p-4 border-b border-gray-200">
          <h2 className="font-semibold text-gray-900">Backup History</h2>
        </div>

        <div className="divide-y divide-gray-100">
          {backups?.map((backup) => (
            <div key={backup.id} className="p-4 hover:bg-gray-50">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  {getTypeIcon(backup.type)}
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-900">{backup.name}</span>
                      {getStatusIcon(backup.status)}
                    </div>
                    <div className="flex items-center gap-4 text-sm text-gray-500 mt-1">
                      <span>{formatDate(backup.createdAt)}</span>
                      {backup.size && <span>{backup.size}</span>}
                      <span className="capitalize">{backup.type}</span>
                    </div>
                    {backup.error && (
                      <p className="text-sm text-red-600 mt-1 flex items-center gap-1">
                        <AlertTriangle className="h-4 w-4" />
                        {backup.error}
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {backup.status === 'completed' && (
                    <>
                      <button
                        onClick={() => setShowRestoreConfirm(backup)}
                        className="btn btn-secondary text-sm"
                      >
                        <RefreshCw className="h-4 w-4 mr-1" />
                        Restore
                      </button>
                      <button className="btn btn-secondary text-sm">
                        <Download className="h-4 w-4 mr-1" />
                        Download
                      </button>
                    </>
                  )}
                  <button
                    onClick={() => deleteBackupMutation.mutate(backup.id)}
                    className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>

              {/* Backup includes */}
              <div className="mt-3 flex items-center gap-2">
                {backup.includes?.map((item) => (
                  <span
                    key={item}
                    className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded capitalize"
                  >
                    {item}
                  </span>
                ))}
              </div>
            </div>
          ))}

          {(!backups || backups.length === 0) && (
            <div className="p-12 text-center">
              <Database className="h-12 w-12 text-gray-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No Backups Yet</h3>
              <p className="text-gray-500 mb-4">Create your first backup to protect your data</p>
              <button
                onClick={() => setShowCreateBackup(true)}
                className="btn btn-primary"
              >
                Create Backup
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Create Backup Modal */}
      {showCreateBackup && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4">
            <div className="fixed inset-0 bg-black/50" onClick={() => setShowCreateBackup(false)} />
            <div className="relative bg-white rounded-xl shadow-xl max-w-md w-full p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Create New Backup</h3>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Backup Name (optional)
                  </label>
                  <input
                    type="text"
                    value={backupOptions.name}
                    onChange={(e) => setBackupOptions({ ...backupOptions, name: e.target.value })}
                    className="input"
                    placeholder="e.g., Pre-update Backup"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Include in Backup
                  </label>
                  <div className="space-y-2">
                    {[
                      { key: 'includeDatabase', label: 'Database', desc: 'All content, users, and settings' },
                      { key: 'includeMedia', label: 'Media Files', desc: 'Uploaded images, videos, and documents' },
                      { key: 'includeConfig', label: 'Configuration', desc: 'Site settings and customizations' },
                    ].map((option) => (
                      <label key={option.key} className="flex items-start gap-3 p-3 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={backupOptions[option.key]}
                          onChange={(e) => setBackupOptions({ ...backupOptions, [option.key]: e.target.checked })}
                          className="mt-0.5 h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                        />
                        <div>
                          <span className="font-medium text-gray-900">{option.label}</span>
                          <p className="text-sm text-gray-500">{option.desc}</p>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowCreateBackup(false)}
                  className="btn btn-secondary flex-1"
                >
                  Cancel
                </button>
                <button
                  onClick={() => createBackupMutation.mutate(backupOptions)}
                  disabled={createBackupMutation.isPending || (!backupOptions.includeDatabase && !backupOptions.includeMedia && !backupOptions.includeConfig)}
                  className="btn btn-primary flex-1"
                >
                  {createBackupMutation.isPending ? 'Creating...' : 'Create Backup'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Restore Confirmation Modal */}
      {showRestoreConfirm && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4">
            <div className="fixed inset-0 bg-black/50" onClick={() => setShowRestoreConfirm(null)} />
            <div className="relative bg-white rounded-xl shadow-xl max-w-md w-full p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="h-10 w-10 bg-amber-100 rounded-full flex items-center justify-center">
                  <AlertTriangle className="h-5 w-5 text-amber-600" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900">Restore Backup</h3>
              </div>

              <p className="text-gray-600 mb-4">
                Are you sure you want to restore from <strong>{showRestoreConfirm.name}</strong>?
                This will replace your current data with the backup from {formatDate(showRestoreConfirm.createdAt)}.
              </p>

              <div className="bg-red-50 rounded-lg p-4 mb-4">
                <p className="text-sm text-red-800">
                  <strong>Warning:</strong> This action cannot be undone. We recommend creating a backup of your current data before proceeding.
                </p>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => setShowRestoreConfirm(null)}
                  className="btn btn-secondary flex-1"
                >
                  Cancel
                </button>
                <button
                  onClick={() => restoreBackupMutation.mutate(showRestoreConfirm.id)}
                  disabled={restoreBackupMutation.isPending}
                  className="btn bg-red-600 text-white hover:bg-red-700 flex-1"
                >
                  {restoreBackupMutation.isPending ? 'Restoring...' : 'Restore Backup'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Schedule Settings Modal */}
      {showScheduleSettings && schedule && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4">
            <div className="fixed inset-0 bg-black/50" onClick={() => setShowScheduleSettings(false)} />
            <div className="relative bg-white rounded-xl shadow-xl max-w-md w-full p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Backup Schedule</h3>

              <div className="space-y-4">
                <div className="flex items-center gap-4">
                  <input
                    type="checkbox"
                    id="scheduleEnabled"
                    checked={schedule.enabled}
                    onChange={(e) => updateScheduleMutation.mutate({ ...schedule, enabled: e.target.checked })}
                    className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  <label htmlFor="scheduleEnabled" className="font-medium text-gray-900">
                    Enable automatic backups
                  </label>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Frequency</label>
                  <select className="input">
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly</option>
                    <option value="monthly">Monthly</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Time</label>
                  <input type="time" defaultValue="03:00" className="input" />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Keep backups for (days)
                  </label>
                  <input type="number" defaultValue={7} min={1} max={365} className="input" />
                </div>

                <div className="flex items-center gap-4">
                  <input
                    type="checkbox"
                    id="includeMedia"
                    defaultChecked
                    className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  <label htmlFor="includeMedia" className="text-gray-700">
                    Include media files in backups
                  </label>
                </div>
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowScheduleSettings(false)}
                  className="btn btn-secondary flex-1"
                >
                  Cancel
                </button>
                <button className="btn btn-primary flex-1">
                  Save Schedule
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default BackupRestorePage
