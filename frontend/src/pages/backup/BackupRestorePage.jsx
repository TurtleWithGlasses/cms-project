import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { backupApi } from '../../services/api'
import { Card, CardContent } from '../../components/ui/Card'
import { useToast } from '../../components/ui/Toast'
import { Skeleton } from '../../components/ui/Skeleton'
import {
  Database,
  Download,
  Clock,
  HardDrive,
  Trash2,
  RefreshCw,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Calendar,
  FileArchive,
  Settings,
  AlertCircle,
} from 'lucide-react'

function BackupRestorePage() {
  const [showCreateBackup, setShowCreateBackup] = useState(false)
  const [showRestoreConfirm, setShowRestoreConfirm] = useState(null)
  const [showScheduleSettings, setShowScheduleSettings] = useState(false)
  const [backupOptions, setBackupOptions] = useState({
    name: '',
    include_database: true,
    include_media: true,
    include_config: true,
  })
  const [scheduleForm, setScheduleForm] = useState(null)

  const { toast } = useToast()
  const queryClient = useQueryClient()

  // Fetch backups
  const { data: backupsData, isLoading: loadingBackups, error: backupsError, refetch: refetchBackups } = useQuery({
    queryKey: ['backups'],
    queryFn: () => backupApi.getAll(),
    select: (res) => res.data,
  })

  // Fetch schedule
  const { data: schedule, isLoading: loadingSchedule, error: scheduleError } = useQuery({
    queryKey: ['backup-schedule'],
    queryFn: () => backupApi.getSchedule(),
    select: (res) => res.data,
    onSuccess: (data) => {
      if (!scheduleForm) {
        setScheduleForm(data)
      }
    },
  })

  // Fetch storage info
  const { data: storage, isLoading: loadingStorage, error: storageError } = useQuery({
    queryKey: ['backup-storage'],
    queryFn: () => backupApi.getStorageInfo(),
    select: (res) => res.data,
  })

  const backups = backupsData?.items || backupsData || []

  // Create backup mutation
  const createBackupMutation = useMutation({
    mutationFn: (options) => backupApi.create(options),
    onSuccess: () => {
      queryClient.invalidateQueries(['backups'])
      queryClient.invalidateQueries(['backup-storage'])
      setShowCreateBackup(false)
      setBackupOptions({ name: '', include_database: true, include_media: true, include_config: true })
      toast({ title: 'Backup started', description: 'Your backup is being created.', variant: 'success' })
    },
    onError: (error) => {
      toast({
        title: 'Failed to create backup',
        description: error.response?.data?.detail || error.message || 'An error occurred.',
        variant: 'error',
      })
    },
  })

  // Delete backup mutation
  const deleteBackupMutation = useMutation({
    mutationFn: (id) => backupApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries(['backups'])
      queryClient.invalidateQueries(['backup-storage'])
      toast({ title: 'Backup deleted', description: 'The backup has been removed.', variant: 'success' })
    },
    onError: (error) => {
      toast({
        title: 'Failed to delete backup',
        description: error.response?.data?.detail || error.message || 'An error occurred.',
        variant: 'error',
      })
    },
  })

  // Restore backup mutation
  const restoreBackupMutation = useMutation({
    mutationFn: (id) => backupApi.restore(id),
    onSuccess: () => {
      setShowRestoreConfirm(null)
      toast({ title: 'Restore started', description: 'Your site is being restored from backup.', variant: 'success' })
    },
    onError: (error) => {
      toast({
        title: 'Failed to restore backup',
        description: error.response?.data?.detail || error.message || 'An error occurred.',
        variant: 'error',
      })
    },
  })

  // Download backup
  const handleDownload = async (backup) => {
    try {
      const response = await backupApi.download(backup.id)
      const blob = new Blob([response.data], { type: 'application/zip' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${backup.name || 'backup'}-${new Date(backup.created_at).toISOString().split('T')[0]}.zip`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      toast({ title: 'Download started', variant: 'success' })
    } catch (error) {
      toast({
        title: 'Failed to download backup',
        description: error.response?.data?.detail || error.message || 'An error occurred.',
        variant: 'error',
      })
    }
  }

  // Update schedule mutation
  const updateScheduleMutation = useMutation({
    mutationFn: (data) => backupApi.updateSchedule(data),
    onSuccess: () => {
      queryClient.invalidateQueries(['backup-schedule'])
      setShowScheduleSettings(false)
      toast({ title: 'Schedule updated', description: 'Backup schedule has been saved.', variant: 'success' })
    },
    onError: (error) => {
      toast({
        title: 'Failed to update schedule',
        description: error.response?.data?.detail || error.message || 'An error occurred.',
        variant: 'error',
      })
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
        return <FileArchive className="h-5 w-5 text-primary-600 dark:text-primary-400" />
      case 'database':
        return <Database className="h-5 w-5 text-blue-600 dark:text-blue-400" />
      case 'media':
        return <HardDrive className="h-5 w-5 text-purple-600 dark:text-purple-400" />
      default:
        return <FileArchive className="h-5 w-5 text-gray-600 dark:text-gray-400" />
    }
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const formatSize = (bytes) => {
    if (!bytes) return 'N/A'
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(1024))
    return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`
  }

  const hasError = backupsError || scheduleError || storageError

  if (hasError) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Backup & Restore</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">Manage your site backups and restore points</p>
        </div>
        <div className="flex flex-col items-center justify-center py-16 space-y-4">
          <AlertCircle className="h-12 w-12 text-red-500" />
          <div className="text-center">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Failed to load backup data</h2>
            <p className="text-gray-600 dark:text-gray-400 mt-1">
              {backupsError?.message || scheduleError?.message || storageError?.message || 'An error occurred.'}
            </p>
          </div>
          <button
            onClick={() => {
              refetchBackups()
              queryClient.invalidateQueries(['backup-schedule'])
              queryClient.invalidateQueries(['backup-storage'])
            }}
            className="btn btn-secondary flex items-center gap-2"
          >
            <RefreshCw className="h-4 w-4" />
            Retry
          </button>
        </div>
      </div>
    )
  }

  const isLoading = loadingBackups || loadingSchedule || loadingStorage
  const storagePercentage = storage ? (storage.used / storage.total) * 100 : 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Backup & Restore</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">Manage your site backups and restore points</p>
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
        <Card>
          <CardContent className="p-5">
            {loadingStorage ? (
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <Skeleton className="h-10 w-10 rounded-lg" />
                  <div className="space-y-2">
                    <Skeleton className="h-4 w-20" />
                    <Skeleton className="h-6 w-32" />
                  </div>
                </div>
                <Skeleton className="h-2 w-full rounded-full" />
              </div>
            ) : (
              <>
                <div className="flex items-center gap-3 mb-3">
                  <div className="h-10 w-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                    <HardDrive className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Storage Used</p>
                    <p className="text-xl font-semibold text-gray-900 dark:text-white">
                      {storage?.used?.toFixed(1) || 0} GB{' '}
                      <span className="text-sm font-normal text-gray-500 dark:text-gray-400">
                        / {storage?.total || 0} GB
                      </span>
                    </p>
                  </div>
                </div>
                <div className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${
                      storagePercentage > 80
                        ? 'bg-red-500'
                        : storagePercentage > 60
                        ? 'bg-amber-500'
                        : 'bg-blue-500'
                    }`}
                    style={{ width: `${Math.min(storagePercentage, 100)}%` }}
                  />
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* Backup Count */}
        <Card>
          <CardContent className="p-5">
            {loadingStorage ? (
              <div className="flex items-center gap-3">
                <Skeleton className="h-10 w-10 rounded-lg" />
                <div className="space-y-2">
                  <Skeleton className="h-4 w-20" />
                  <Skeleton className="h-6 w-16" />
                </div>
              </div>
            ) : (
              <>
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
                    <FileArchive className="h-5 w-5 text-green-600 dark:text-green-400" />
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Total Backups</p>
                    <p className="text-xl font-semibold text-gray-900 dark:text-white">
                      {storage?.backups_count || backups.length || 0}
                    </p>
                  </div>
                </div>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
                  Oldest: {storage?.oldest_backup ? formatDate(storage.oldest_backup) : 'N/A'}
                </p>
              </>
            )}
          </CardContent>
        </Card>

        {/* Schedule Status */}
        <Card>
          <CardContent className="p-5">
            {loadingSchedule ? (
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Skeleton className="h-10 w-10 rounded-lg" />
                  <div className="space-y-2">
                    <Skeleton className="h-4 w-20" />
                    <Skeleton className="h-6 w-24" />
                  </div>
                </div>
                <Skeleton className="h-8 w-8 rounded-lg" />
              </div>
            ) : (
              <>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div
                      className={`h-10 w-10 rounded-lg flex items-center justify-center ${
                        schedule?.enabled
                          ? 'bg-primary-100 dark:bg-primary-900/30'
                          : 'bg-gray-100 dark:bg-gray-700'
                      }`}
                    >
                      <Clock
                        className={`h-5 w-5 ${
                          schedule?.enabled
                            ? 'text-primary-600 dark:text-primary-400'
                            : 'text-gray-400'
                        }`}
                      />
                    </div>
                    <div>
                      <p className="text-sm text-gray-500 dark:text-gray-400">Auto Backup</p>
                      <p className="text-xl font-semibold text-gray-900 dark:text-white">
                        {schedule?.enabled ? `Every ${schedule.frequency}` : 'Disabled'}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => {
                      setScheduleForm(schedule)
                      setShowScheduleSettings(true)
                    }}
                    className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
                  >
                    <Settings className="h-5 w-5 text-gray-400" />
                  </button>
                </div>
                {schedule?.enabled && schedule?.next_run && (
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
                    Next: {formatDate(schedule.next_run)}
                  </p>
                )}
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Backups List */}
      <Card>
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="font-semibold text-gray-900 dark:text-white">Backup History</h2>
        </div>

        <CardContent className="p-0">
          {loadingBackups ? (
            <div className="divide-y divide-gray-100 dark:divide-gray-700">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="p-4">
                  <div className="flex items-center gap-4">
                    <Skeleton className="h-10 w-10 rounded-lg" />
                    <div className="flex-1 space-y-2">
                      <Skeleton className="h-5 w-40" />
                      <Skeleton className="h-4 w-64" />
                    </div>
                    <Skeleton className="h-9 w-24 rounded-lg" />
                    <Skeleton className="h-9 w-24 rounded-lg" />
                  </div>
                </div>
              ))}
            </div>
          ) : backups.length === 0 ? (
            <div className="p-12 text-center">
              <Database className="h-12 w-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">No Backups Yet</h3>
              <p className="text-gray-500 dark:text-gray-400 mb-4">
                Create your first backup to protect your data
              </p>
              <button onClick={() => setShowCreateBackup(true)} className="btn btn-primary">
                Create Backup
              </button>
            </div>
          ) : (
            <div className="divide-y divide-gray-100 dark:divide-gray-700">
              {backups.map((backup) => (
                <div
                  key={backup.id}
                  className="p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      {getTypeIcon(backup.type)}
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-gray-900 dark:text-white">
                            {backup.name || 'Backup'}
                          </span>
                          {getStatusIcon(backup.status)}
                        </div>
                        <div className="flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400 mt-1">
                          <span>{formatDate(backup.created_at)}</span>
                          {backup.size && <span>{formatSize(backup.size)}</span>}
                          <span className="capitalize">{backup.type}</span>
                        </div>
                        {backup.error && (
                          <p className="text-sm text-red-600 dark:text-red-400 mt-1 flex items-center gap-1">
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
                          <button
                            onClick={() => handleDownload(backup)}
                            className="btn btn-secondary text-sm"
                          >
                            <Download className="h-4 w-4 mr-1" />
                            Download
                          </button>
                        </>
                      )}
                      <button
                        onClick={() => {
                          if (window.confirm('Are you sure you want to delete this backup?')) {
                            deleteBackupMutation.mutate(backup.id)
                          }
                        }}
                        disabled={deleteBackupMutation.isPending}
                        className="p-2 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg disabled:opacity-50"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>

                  {/* Backup includes */}
                  {backup.includes && backup.includes.length > 0 && (
                    <div className="mt-3 flex items-center gap-2">
                      {backup.includes.map((item) => (
                        <span
                          key={item}
                          className="text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 px-2 py-1 rounded capitalize"
                        >
                          {item}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create Backup Modal */}
      {showCreateBackup && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4">
            <div
              className="fixed inset-0 bg-black/50"
              onClick={() => setShowCreateBackup(false)}
            />
            <div className="relative bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-md w-full p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Create New Backup
              </h3>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Backup Name (optional)
                  </label>
                  <input
                    type="text"
                    value={backupOptions.name}
                    onChange={(e) =>
                      setBackupOptions({ ...backupOptions, name: e.target.value })
                    }
                    className="input dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                    placeholder="e.g., Pre-update Backup"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Include in Backup
                  </label>
                  <div className="space-y-2">
                    {[
                      {
                        key: 'include_database',
                        label: 'Database',
                        desc: 'All content, users, and settings',
                      },
                      {
                        key: 'include_media',
                        label: 'Media Files',
                        desc: 'Uploaded images, videos, and documents',
                      },
                      {
                        key: 'include_config',
                        label: 'Configuration',
                        desc: 'Site settings and customizations',
                      },
                    ].map((option) => (
                      <label
                        key={option.key}
                        className="flex items-start gap-3 p-3 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer"
                      >
                        <input
                          type="checkbox"
                          checked={backupOptions[option.key]}
                          onChange={(e) =>
                            setBackupOptions({
                              ...backupOptions,
                              [option.key]: e.target.checked,
                            })
                          }
                          className="mt-0.5 h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                        />
                        <div>
                          <span className="font-medium text-gray-900 dark:text-white">
                            {option.label}
                          </span>
                          <p className="text-sm text-gray-500 dark:text-gray-400">{option.desc}</p>
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
                  disabled={
                    createBackupMutation.isPending ||
                    (!backupOptions.include_database &&
                      !backupOptions.include_media &&
                      !backupOptions.include_config)
                  }
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
            <div
              className="fixed inset-0 bg-black/50"
              onClick={() => setShowRestoreConfirm(null)}
            />
            <div className="relative bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-md w-full p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="h-10 w-10 bg-amber-100 dark:bg-amber-900/30 rounded-full flex items-center justify-center">
                  <AlertTriangle className="h-5 w-5 text-amber-600 dark:text-amber-400" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Restore Backup
                </h3>
              </div>

              <p className="text-gray-600 dark:text-gray-400 mb-4">
                Are you sure you want to restore from{' '}
                <strong className="text-gray-900 dark:text-white">
                  {showRestoreConfirm.name || 'this backup'}
                </strong>
                ? This will replace your current data with the backup from{' '}
                {formatDate(showRestoreConfirm.created_at)}.
              </p>

              <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-4 mb-4">
                <p className="text-sm text-red-800 dark:text-red-300">
                  <strong>Warning:</strong> This action cannot be undone. We recommend creating a
                  backup of your current data before proceeding.
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
      {showScheduleSettings && scheduleForm && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4">
            <div
              className="fixed inset-0 bg-black/50"
              onClick={() => setShowScheduleSettings(false)}
            />
            <div className="relative bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-md w-full p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Backup Schedule
              </h3>

              <div className="space-y-4">
                <div className="flex items-center gap-4">
                  <input
                    type="checkbox"
                    id="scheduleEnabled"
                    checked={scheduleForm.enabled}
                    onChange={(e) =>
                      setScheduleForm({ ...scheduleForm, enabled: e.target.checked })
                    }
                    className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  <label
                    htmlFor="scheduleEnabled"
                    className="font-medium text-gray-900 dark:text-white"
                  >
                    Enable automatic backups
                  </label>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Frequency
                  </label>
                  <select
                    value={scheduleForm.frequency}
                    onChange={(e) =>
                      setScheduleForm({ ...scheduleForm, frequency: e.target.value })
                    }
                    className="input dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                  >
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly</option>
                    <option value="monthly">Monthly</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Time
                  </label>
                  <input
                    type="time"
                    value={scheduleForm.time || '03:00'}
                    onChange={(e) => setScheduleForm({ ...scheduleForm, time: e.target.value })}
                    className="input dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Keep backups for (days)
                  </label>
                  <input
                    type="number"
                    value={scheduleForm.retention || 7}
                    onChange={(e) =>
                      setScheduleForm({ ...scheduleForm, retention: parseInt(e.target.value) })
                    }
                    min={1}
                    max={365}
                    className="input dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                  />
                </div>

                <div className="flex items-center gap-4">
                  <input
                    type="checkbox"
                    id="includeMediaSchedule"
                    checked={scheduleForm.include_media}
                    onChange={(e) =>
                      setScheduleForm({ ...scheduleForm, include_media: e.target.checked })
                    }
                    className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  <label
                    htmlFor="includeMediaSchedule"
                    className="text-gray-700 dark:text-gray-300"
                  >
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
                <button
                  onClick={() => updateScheduleMutation.mutate(scheduleForm)}
                  disabled={updateScheduleMutation.isPending}
                  className="btn btn-primary flex-1"
                >
                  {updateScheduleMutation.isPending ? 'Saving...' : 'Save Schedule'}
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
