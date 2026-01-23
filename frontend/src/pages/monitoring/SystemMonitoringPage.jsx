import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { monitoringApi } from '../../services/api'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card'
import Button from '../../components/ui/Button'
import {
  Activity,
  Server,
  Database,
  HardDrive,
  Clock,
  RefreshCw,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Zap,
  Globe,
  Loader2,
} from 'lucide-react'

function StatusBadge({ status }) {
  const styles = {
    healthy: { bg: 'bg-green-100 dark:bg-green-900/50', text: 'text-green-700 dark:text-green-400', icon: CheckCircle },
    degraded: { bg: 'bg-yellow-100 dark:bg-yellow-900/50', text: 'text-yellow-700 dark:text-yellow-400', icon: AlertTriangle },
    unhealthy: { bg: 'bg-red-100 dark:bg-red-900/50', text: 'text-red-700 dark:text-red-400', icon: XCircle },
    ready: { bg: 'bg-green-100 dark:bg-green-900/50', text: 'text-green-700 dark:text-green-400', icon: CheckCircle },
    not_ready: { bg: 'bg-red-100 dark:bg-red-900/50', text: 'text-red-700 dark:text-red-400', icon: XCircle },
  }
  const style = styles[status] || styles.healthy
  const Icon = style.icon

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${style.bg} ${style.text}`}>
      <Icon className="h-3 w-3" />
      {status.charAt(0).toUpperCase() + status.slice(1).replace('_', ' ')}
    </span>
  )
}

function formatUptime(seconds) {
  if (!seconds) return 'N/A'
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)

  const parts = []
  if (days > 0) parts.push(`${days} day${days !== 1 ? 's' : ''}`)
  if (hours > 0) parts.push(`${hours} hour${hours !== 1 ? 's' : ''}`)
  if (minutes > 0 && days === 0) parts.push(`${minutes} min${minutes !== 1 ? 's' : ''}`)

  return parts.join(', ') || 'Just started'
}

function ServiceCard({ title, icon: Icon, status, latency, message, extra }) {
  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Icon className="h-5 w-5 text-gray-500 dark:text-gray-400" />
            <span className="font-medium text-gray-900 dark:text-gray-100">{title}</span>
          </div>
          <StatusBadge status={status || 'unhealthy'} />
        </div>
        <div className="text-sm text-gray-500 dark:text-gray-400 space-y-1">
          {latency !== undefined && (
            <div>Latency: <span className="font-medium text-gray-900 dark:text-gray-100">{latency}ms</span></div>
          )}
          {message && <div className="truncate" title={message}>{message}</div>}
          {extra}
        </div>
      </CardContent>
    </Card>
  )
}

function SystemMonitoringPage() {
  const [autoRefresh, setAutoRefresh] = useState(true)

  // Fetch detailed health data
  const { data: healthData, isLoading: healthLoading, error: healthError, refetch: refetchHealth } = useQuery({
    queryKey: ['monitoring', 'health', 'detailed'],
    queryFn: async () => {
      const response = await monitoringApi.getDetailedHealth()
      return response.data
    },
    refetchInterval: autoRefresh ? 30000 : false,
  })

  // Fetch basic health for quick status
  const { data: basicHealth } = useQuery({
    queryKey: ['monitoring', 'health', 'basic'],
    queryFn: async () => {
      const response = await monitoringApi.getHealth()
      return response.data
    },
    refetchInterval: autoRefresh ? 30000 : false,
  })

  // Fetch readiness status
  const { data: readinessData } = useQuery({
    queryKey: ['monitoring', 'readiness'],
    queryFn: async () => {
      const response = await monitoringApi.getReadiness()
      return response.data
    },
    refetchInterval: autoRefresh ? 30000 : false,
  })

  const refetchAll = () => {
    refetchHealth()
  }

  const isLoading = healthLoading

  // Extract data with fallbacks
  const status = healthData?.status || basicHealth?.status || 'unknown'
  const version = healthData?.version || basicHealth?.version || 'N/A'
  const environment = healthData?.environment || 'N/A'
  const uptime = healthData?.uptime_seconds || basicHealth?.uptime_seconds || 0
  const checks = healthData?.checks || {}
  const timestamp = healthData?.timestamp || basicHealth?.timestamp

  // Use readiness checks as fallback for service status
  const dbCheck = checks.database || readinessData?.checks?.database || {}
  const redisCheck = checks.redis || readinessData?.checks?.redis || {}
  const diskCheck = checks.disk || {}
  const memoryCheck = checks.memory || {}

  if (healthError) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <AlertTriangle className="h-12 w-12 text-yellow-500 mb-4" />
        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">Unable to connect to monitoring</h3>
        <p className="text-gray-500 dark:text-gray-400 mt-1">{healthError.message}</p>
        <Button onClick={refetchAll} className="mt-4">
          <RefreshCw className="h-4 w-4 mr-2" />
          Retry
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">System Monitoring</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">Real-time system health and status</p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="h-4 w-4 text-primary-600 rounded border-gray-300 dark:border-gray-600 focus:ring-primary-500"
            />
            Auto-refresh
          </label>
          <Button variant="outline" onClick={refetchAll} disabled={isLoading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Overall Status */}
      <Card>
        <CardContent className="p-4">
          {isLoading ? (
            <div className="flex items-center justify-center py-4">
              <Loader2 className="h-6 w-6 animate-spin text-primary-600" />
            </div>
          ) : (
            <div className="flex flex-wrap items-center gap-6 text-sm">
              <div className="flex items-center gap-2">
                <Activity className="h-4 w-4 text-gray-400" />
                <span className="text-gray-500 dark:text-gray-400">Status:</span>
                <StatusBadge status={status} />
              </div>
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-gray-400" />
                <span className="text-gray-500 dark:text-gray-400">Uptime:</span>
                <span className="font-medium text-gray-900 dark:text-gray-100">{formatUptime(uptime)}</span>
              </div>
              <div className="flex items-center gap-2">
                <Server className="h-4 w-4 text-gray-400" />
                <span className="text-gray-500 dark:text-gray-400">Version:</span>
                <span className="font-medium text-gray-900 dark:text-gray-100">{version}</span>
              </div>
              <div className="flex items-center gap-2">
                <Globe className="h-4 w-4 text-gray-400" />
                <span className="text-gray-500 dark:text-gray-400">Environment:</span>
                <span className="font-medium text-gray-900 dark:text-gray-100 capitalize">{environment}</span>
              </div>
              {timestamp && (
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-gray-400" />
                  <span className="text-gray-500 dark:text-gray-400">Last check:</span>
                  <span className="font-medium text-gray-900 dark:text-gray-100">
                    {new Date(timestamp).toLocaleTimeString()}
                  </span>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Service Health Status */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {isLoading ? (
          [...Array(4)].map((_, i) => (
            <Card key={i}>
              <CardContent className="p-6">
                <div className="animate-pulse space-y-4">
                  <div className="h-5 bg-gray-200 dark:bg-gray-700 rounded w-3/4" />
                  <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2" />
                </div>
              </CardContent>
            </Card>
          ))
        ) : (
          <>
            <ServiceCard
              title="API Server"
              icon={Server}
              status={status}
              message="Application is running"
            />
            <ServiceCard
              title="Database"
              icon={Database}
              status={dbCheck.status}
              latency={dbCheck.latency_ms}
              message={dbCheck.message}
            />
            <ServiceCard
              title="Redis Cache"
              icon={Zap}
              status={redisCheck.status}
              latency={redisCheck.latency_ms}
              message={redisCheck.message || redisCheck.error}
            />
            <ServiceCard
              title="Storage"
              icon={HardDrive}
              status={diskCheck.status || 'healthy'}
              message={diskCheck.message || 'Storage available'}
            />
          </>
        )}
      </div>

      {/* Readiness Status */}
      {readinessData && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Readiness Status
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-4 mb-4">
              <StatusBadge status={readinessData.status} />
              <span className="text-sm text-gray-500 dark:text-gray-400">
                {readinessData.status === 'ready'
                  ? 'All services are ready to handle requests'
                  : 'Some services are not ready'}
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Object.entries(readinessData.checks || {}).map(([service, check]) => (
                <div
                  key={service}
                  className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
                >
                  <span className="font-medium text-gray-900 dark:text-gray-100 capitalize">{service}</span>
                  <div className="flex items-center gap-2">
                    {check.latency_ms && (
                      <span className="text-sm text-gray-500 dark:text-gray-400">{check.latency_ms}ms</span>
                    )}
                    <StatusBadge status={check.status} />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* System Info Card */}
      <Card>
        <CardHeader>
          <CardTitle>System Information</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div>
                <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Memory</h4>
                <div className="flex items-center gap-2">
                  <StatusBadge status={memoryCheck.status || 'healthy'} />
                  <span className="text-sm text-gray-600 dark:text-gray-300">{memoryCheck.message || 'Memory available'}</span>
                </div>
              </div>
              <div>
                <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Disk</h4>
                <div className="flex items-center gap-2">
                  <StatusBadge status={diskCheck.status || 'healthy'} />
                  <span className="text-sm text-gray-600 dark:text-gray-300">{diskCheck.message || 'Disk space available'}</span>
                </div>
              </div>
            </div>
            <div className="space-y-4">
              <div>
                <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Application Version</h4>
                <span className="text-lg font-semibold text-gray-900 dark:text-gray-100">{version}</span>
              </div>
              <div>
                <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Total Uptime</h4>
                <span className="text-lg font-semibold text-gray-900 dark:text-gray-100">{formatUptime(uptime)}</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default SystemMonitoringPage
