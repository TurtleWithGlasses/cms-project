import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { monitoringApi } from '../../services/api'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card'
import Button from '../../components/ui/Button'
import {
  Activity,
  Server,
  Database,
  HardDrive,
  Cpu,
  MemoryStick,
  Clock,
  RefreshCw,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Zap,
  Globe,
  Users,
} from 'lucide-react'

// Mock data for demo
const mockMonitoringData = {
  system: {
    uptime: '14 days, 7 hours',
    version: '1.0.0',
    environment: 'production',
    lastDeployment: '2024-01-15T10:30:00Z',
  },
  health: {
    api: { status: 'healthy', latency: 45 },
    database: { status: 'healthy', latency: 12, connections: 25 },
    redis: { status: 'healthy', latency: 3, memory: '128MB' },
    storage: { status: 'healthy', used: '45GB', total: '100GB' },
  },
  performance: {
    cpu: 35,
    memory: 62,
    disk: 45,
    requests: 1250,
    avgResponseTime: 145,
    errorRate: 0.2,
  },
  recentErrors: [
    { time: '2024-01-18T14:23:00Z', type: 'ValidationError', message: 'Invalid email format', count: 3 },
    { time: '2024-01-18T12:15:00Z', type: 'RateLimitError', message: 'Rate limit exceeded', count: 12 },
    { time: '2024-01-18T10:45:00Z', type: 'DatabaseError', message: 'Connection timeout', count: 1 },
  ],
  metrics: {
    requestsToday: 45280,
    requestsYesterday: 42150,
    activeUsers: 128,
    cacheHitRate: 94.5,
    avgQueryTime: 8.2,
  },
}

function StatusBadge({ status }) {
  const styles = {
    healthy: { bg: 'bg-green-100', text: 'text-green-700', icon: CheckCircle },
    degraded: { bg: 'bg-yellow-100', text: 'text-yellow-700', icon: AlertTriangle },
    unhealthy: { bg: 'bg-red-100', text: 'text-red-700', icon: XCircle },
  }
  const style = styles[status] || styles.healthy
  const Icon = style.icon

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${style.bg} ${style.text}`}>
      <Icon className="h-3 w-3" />
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  )
}

function MetricCard({ title, value, subtitle, icon: Icon, color, trend }) {
  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-500">{title}</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
            {subtitle && <p className="text-xs text-gray-500 mt-1">{subtitle}</p>}
          </div>
          <div className={`h-12 w-12 rounded-lg flex items-center justify-center ${color}`}>
            <Icon className="h-6 w-6 text-white" />
          </div>
        </div>
        {trend !== undefined && (
          <div className={`mt-3 text-sm ${trend >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {trend >= 0 ? '+' : ''}{trend}% from yesterday
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function ProgressBar({ value, max = 100, color = 'bg-primary-500' }) {
  const percentage = Math.min((value / max) * 100, 100)
  const bgColor = percentage > 80 ? 'bg-red-500' : percentage > 60 ? 'bg-yellow-500' : color

  return (
    <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
      <div
        className={`h-full ${bgColor} transition-all`}
        style={{ width: `${percentage}%` }}
      />
    </div>
  )
}

function SystemMonitoringPage() {
  const [autoRefresh, setAutoRefresh] = useState(true)

  const { data: monitoring = mockMonitoringData, isLoading, refetch } = useQuery({
    queryKey: ['monitoring'],
    queryFn: () => monitoringApi.getHealth(),
    select: (res) => res.data || mockMonitoringData,
    placeholderData: mockMonitoringData,
    refetchInterval: autoRefresh ? 30000 : false, // Refresh every 30 seconds
  })

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString()
  }

  const requestsTrend = Math.round(
    ((monitoring.metrics.requestsToday - monitoring.metrics.requestsYesterday) /
      monitoring.metrics.requestsYesterday) *
      100
  )

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">System Monitoring</h1>
          <p className="text-gray-500 mt-1">Real-time system health and performance metrics</p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-gray-600">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="h-4 w-4 text-primary-600 rounded border-gray-300 focus:ring-primary-500"
            />
            Auto-refresh
          </label>
          <Button variant="outline" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* System info */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-wrap items-center gap-6 text-sm">
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-gray-400" />
              <span className="text-gray-500">Uptime:</span>
              <span className="font-medium">{monitoring.system.uptime}</span>
            </div>
            <div className="flex items-center gap-2">
              <Server className="h-4 w-4 text-gray-400" />
              <span className="text-gray-500">Version:</span>
              <span className="font-medium">{monitoring.system.version}</span>
            </div>
            <div className="flex items-center gap-2">
              <Globe className="h-4 w-4 text-gray-400" />
              <span className="text-gray-500">Environment:</span>
              <span className="font-medium capitalize">{monitoring.system.environment}</span>
            </div>
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-gray-400" />
              <span className="text-gray-500">Last Deploy:</span>
              <span className="font-medium">{formatDate(monitoring.system.lastDeployment)}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Health Status */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Server className="h-5 w-5 text-gray-500" />
                <span className="font-medium">API Server</span>
              </div>
              <StatusBadge status={monitoring.health.api.status} />
            </div>
            <div className="text-sm text-gray-500">
              Latency: <span className="font-medium text-gray-900">{monitoring.health.api.latency}ms</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Database className="h-5 w-5 text-gray-500" />
                <span className="font-medium">Database</span>
              </div>
              <StatusBadge status={monitoring.health.database.status} />
            </div>
            <div className="text-sm text-gray-500 space-y-1">
              <div>Latency: <span className="font-medium text-gray-900">{monitoring.health.database.latency}ms</span></div>
              <div>Connections: <span className="font-medium text-gray-900">{monitoring.health.database.connections}</span></div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Zap className="h-5 w-5 text-gray-500" />
                <span className="font-medium">Redis Cache</span>
              </div>
              <StatusBadge status={monitoring.health.redis.status} />
            </div>
            <div className="text-sm text-gray-500 space-y-1">
              <div>Latency: <span className="font-medium text-gray-900">{monitoring.health.redis.latency}ms</span></div>
              <div>Memory: <span className="font-medium text-gray-900">{monitoring.health.redis.memory}</span></div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <HardDrive className="h-5 w-5 text-gray-500" />
                <span className="font-medium">Storage</span>
              </div>
              <StatusBadge status={monitoring.health.storage.status} />
            </div>
            <div className="text-sm text-gray-500">
              <span className="font-medium text-gray-900">{monitoring.health.storage.used}</span> / {monitoring.health.storage.total}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Performance Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Requests Today"
          value={monitoring.metrics.requestsToday.toLocaleString()}
          icon={Activity}
          color="bg-blue-500"
          trend={requestsTrend}
        />
        <MetricCard
          title="Active Users"
          value={monitoring.metrics.activeUsers}
          subtitle="Currently online"
          icon={Users}
          color="bg-green-500"
        />
        <MetricCard
          title="Cache Hit Rate"
          value={`${monitoring.metrics.cacheHitRate}%`}
          subtitle="Last 24 hours"
          icon={Zap}
          color="bg-purple-500"
        />
        <MetricCard
          title="Avg Query Time"
          value={`${monitoring.metrics.avgQueryTime}ms`}
          subtitle="Database queries"
          icon={Database}
          color="bg-orange-500"
        />
      </div>

      {/* Resource Usage */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Resource Usage</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Cpu className="h-4 w-4 text-gray-500" />
                  <span className="text-sm font-medium">CPU Usage</span>
                </div>
                <span className="text-sm font-bold">{monitoring.performance.cpu}%</span>
              </div>
              <ProgressBar value={monitoring.performance.cpu} />
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <MemoryStick className="h-4 w-4 text-gray-500" />
                  <span className="text-sm font-medium">Memory Usage</span>
                </div>
                <span className="text-sm font-bold">{monitoring.performance.memory}%</span>
              </div>
              <ProgressBar value={monitoring.performance.memory} />
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <HardDrive className="h-4 w-4 text-gray-500" />
                  <span className="text-sm font-medium">Disk Usage</span>
                </div>
                <span className="text-sm font-bold">{monitoring.performance.disk}%</span>
              </div>
              <ProgressBar value={monitoring.performance.disk} />
            </div>

            <div className="pt-4 border-t border-gray-200">
              <div className="grid grid-cols-2 gap-4 text-center">
                <div>
                  <p className="text-2xl font-bold text-gray-900">{monitoring.performance.avgResponseTime}ms</p>
                  <p className="text-sm text-gray-500">Avg Response Time</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-900">{monitoring.performance.errorRate}%</p>
                  <p className="text-sm text-gray-500">Error Rate</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Recent Errors */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-yellow-500" />
              Recent Errors
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {monitoring.recentErrors.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                <CheckCircle className="h-12 w-12 mx-auto mb-4 text-green-500" />
                <p>No recent errors</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-200">
                {monitoring.recentErrors.map((error, index) => (
                  <div key={index} className="px-6 py-4">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-medium text-red-600">{error.type}</span>
                      <span className="text-xs text-gray-400">{formatDate(error.time)}</span>
                    </div>
                    <p className="text-sm text-gray-600">{error.message}</p>
                    <span className="text-xs text-gray-400">Occurrences: {error.count}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default SystemMonitoringPage
