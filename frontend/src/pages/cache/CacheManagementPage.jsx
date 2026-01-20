import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { cacheApi } from '../../services/api'
import { useToast } from '../../components/ui/Toast'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card'
import Button from '../../components/ui/Button'
import {
  Database,
  Trash2,
  RefreshCw,
  Zap,
  HardDrive,
  Clock,
  BarChart3,
  AlertCircle,
  CheckCircle,
  Loader2,
  Server,
  FileJson,
  Image,
  Users,
  FileText,
} from 'lucide-react'

// Mock data for demo
const mockCacheStats = {
  overview: {
    totalSize: '256 MB',
    usedSize: '128 MB',
    usedPercentage: 50,
    hitRate: 94.5,
    missRate: 5.5,
    totalKeys: 15420,
    expiredKeys: 342,
  },
  caches: [
    {
      id: 'content',
      name: 'Content Cache',
      icon: FileText,
      size: '45 MB',
      keys: 3250,
      hitRate: 96.2,
      ttl: 3600,
      lastCleared: '2024-01-18T10:00:00Z',
    },
    {
      id: 'api',
      name: 'API Response Cache',
      icon: Server,
      size: '32 MB',
      keys: 5820,
      hitRate: 92.8,
      ttl: 300,
      lastCleared: '2024-01-18T14:30:00Z',
    },
    {
      id: 'session',
      name: 'Session Cache',
      icon: Users,
      size: '18 MB',
      keys: 1250,
      hitRate: 99.1,
      ttl: 1800,
      lastCleared: '2024-01-17T08:00:00Z',
    },
    {
      id: 'media',
      name: 'Media Metadata Cache',
      icon: Image,
      size: '28 MB',
      keys: 4100,
      hitRate: 88.5,
      ttl: 86400,
      lastCleared: '2024-01-15T12:00:00Z',
    },
    {
      id: 'query',
      name: 'Database Query Cache',
      icon: Database,
      size: '5 MB',
      keys: 1000,
      hitRate: 97.3,
      ttl: 600,
      lastCleared: '2024-01-18T16:00:00Z',
    },
  ],
  recentActivity: [
    { action: 'Cache cleared', cache: 'API Response Cache', time: '2024-01-18T14:30:00Z', user: 'System' },
    { action: 'Cache purged', cache: 'Content Cache', time: '2024-01-18T10:00:00Z', user: 'Admin' },
    { action: 'TTL updated', cache: 'Session Cache', time: '2024-01-17T16:45:00Z', user: 'Admin' },
  ],
}

function CacheManagementPage() {
  const queryClient = useQueryClient()
  const toast = useToast()
  const [clearingCache, setClearingCache] = useState(null)

  // Fetch cache stats
  const { data: cacheStats = mockCacheStats, isLoading, refetch } = useQuery({
    queryKey: ['cache-stats'],
    queryFn: () => cacheApi.getStats(),
    select: (res) => res.data || mockCacheStats,
    placeholderData: mockCacheStats,
    refetchInterval: 30000,
  })

  // Clear specific cache mutation
  const clearCacheMutation = useMutation({
    mutationFn: (cacheId) => cacheApi.clear(cacheId),
    onSuccess: (_, cacheId) => {
      queryClient.invalidateQueries({ queryKey: ['cache-stats'] })
      toast.success(`${cacheId} cache cleared successfully`)
      setClearingCache(null)
    },
    onError: () => {
      toast.error('Failed to clear cache')
      setClearingCache(null)
    },
  })

  // Clear all caches mutation
  const clearAllMutation = useMutation({
    mutationFn: () => cacheApi.clearAll(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cache-stats'] })
      toast.success('All caches cleared successfully')
    },
    onError: () => toast.error('Failed to clear caches'),
  })

  const handleClearCache = (cacheId) => {
    setClearingCache(cacheId)
    clearCacheMutation.mutate(cacheId)
  }

  const handleClearAll = () => {
    if (window.confirm('Are you sure you want to clear all caches? This may temporarily slow down the application.')) {
      clearAllMutation.mutate()
    }
  }

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString()
  }

  const formatTTL = (seconds) => {
    if (seconds >= 86400) return `${Math.floor(seconds / 86400)} day(s)`
    if (seconds >= 3600) return `${Math.floor(seconds / 3600)} hour(s)`
    if (seconds >= 60) return `${Math.floor(seconds / 60)} minute(s)`
    return `${seconds} second(s)`
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Cache Management</h1>
          <p className="text-gray-500 mt-1">Monitor and manage application caches</p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          <Button
            onClick={handleClearAll}
            disabled={clearAllMutation.isPending}
            className="bg-red-600 hover:bg-red-700"
          >
            {clearAllMutation.isPending ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Trash2 className="h-4 w-4 mr-2" />
            )}
            Clear All Caches
          </Button>
        </div>
      </div>

      {/* Overview stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="h-12 w-12 bg-blue-100 rounded-lg flex items-center justify-center">
                <HardDrive className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Cache Usage</p>
                <p className="text-2xl font-bold text-gray-900">
                  {cacheStats.overview.usedSize}
                  <span className="text-sm font-normal text-gray-500"> / {cacheStats.overview.totalSize}</span>
                </p>
              </div>
            </div>
            <div className="mt-4 h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={`h-full ${
                  cacheStats.overview.usedPercentage > 80 ? 'bg-red-500' :
                  cacheStats.overview.usedPercentage > 60 ? 'bg-yellow-500' : 'bg-blue-500'
                }`}
                style={{ width: `${cacheStats.overview.usedPercentage}%` }}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="h-12 w-12 bg-green-100 rounded-lg flex items-center justify-center">
                <Zap className="h-6 w-6 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Hit Rate</p>
                <p className="text-2xl font-bold text-gray-900">{cacheStats.overview.hitRate}%</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="h-12 w-12 bg-purple-100 rounded-lg flex items-center justify-center">
                <Database className="h-6 w-6 text-purple-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Total Keys</p>
                <p className="text-2xl font-bold text-gray-900">{cacheStats.overview.totalKeys.toLocaleString()}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="h-12 w-12 bg-yellow-100 rounded-lg flex items-center justify-center">
                <Clock className="h-6 w-6 text-yellow-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Expired Keys</p>
                <p className="text-2xl font-bold text-gray-900">{cacheStats.overview.expiredKeys.toLocaleString()}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Individual caches */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="h-5 w-5" />
            Cache Stores
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="divide-y divide-gray-200">
            {cacheStats.caches.map((cache) => {
              const Icon = cache.icon
              const isClearing = clearingCache === cache.id

              return (
                <div key={cache.id} className="px-6 py-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="h-10 w-10 bg-gray-100 rounded-lg flex items-center justify-center">
                        <Icon className="h-5 w-5 text-gray-600" />
                      </div>
                      <div>
                        <h4 className="font-medium text-gray-900">{cache.name}</h4>
                        <div className="flex items-center gap-4 text-sm text-gray-500 mt-1">
                          <span>{cache.size}</span>
                          <span>{cache.keys.toLocaleString()} keys</span>
                          <span>TTL: {formatTTL(cache.ttl)}</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-6">
                      <div className="text-right">
                        <p className="text-sm font-medium text-gray-900">{cache.hitRate}% hit rate</p>
                        <p className="text-xs text-gray-500">
                          Last cleared: {formatDate(cache.lastCleared)}
                        </p>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleClearCache(cache.id)}
                        disabled={isClearing}
                      >
                        {isClearing ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Trash2 className="h-4 w-4" />
                        )}
                      </Button>
                    </div>
                  </div>

                  {/* Hit rate bar */}
                  <div className="mt-3">
                    <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-green-500"
                        style={{ width: `${cache.hitRate}%` }}
                      />
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* Recent activity */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            Recent Cache Activity
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="divide-y divide-gray-200">
            {cacheStats.recentActivity.map((activity, index) => (
              <div key={index} className="px-6 py-4 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className={`h-8 w-8 rounded-full flex items-center justify-center ${
                    activity.action.includes('cleared') || activity.action.includes('purged')
                      ? 'bg-red-100'
                      : 'bg-blue-100'
                  }`}>
                    {activity.action.includes('cleared') || activity.action.includes('purged') ? (
                      <Trash2 className="h-4 w-4 text-red-600" />
                    ) : (
                      <RefreshCw className="h-4 w-4 text-blue-600" />
                    )}
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">{activity.action}</p>
                    <p className="text-sm text-gray-500">{activity.cache}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm text-gray-500">{formatDate(activity.time)}</p>
                  <p className="text-xs text-gray-400">by {activity.user}</p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Cache tips */}
      <Card>
        <CardContent className="p-6">
          <div className="flex items-start gap-4">
            <div className="h-10 w-10 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
              <AlertCircle className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <h4 className="font-medium text-gray-900">Cache Management Tips</h4>
              <ul className="mt-2 text-sm text-gray-600 space-y-1">
                <li>Clear content cache after bulk content updates</li>
                <li>API cache is automatically cleared when related data changes</li>
                <li>Session cache should only be cleared during maintenance</li>
                <li>High hit rates (90%+) indicate efficient caching</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default CacheManagementPage
