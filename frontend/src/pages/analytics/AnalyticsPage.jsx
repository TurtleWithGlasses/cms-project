import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { analyticsApi } from '../../services/api'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card'
import Button from '../../components/ui/Button'
import {
  BarChart3,
  TrendingUp,
  TrendingDown,
  Eye,
  FileText,
  Users,
  HardDrive,
  Calendar,
  Download,
  RefreshCw,
  ArrowUpRight,
  Loader2,
  AlertCircle,
} from 'lucide-react'

const periods = [
  { value: '7', label: 'Last 7 days' },
  { value: '30', label: 'Last 30 days' },
  { value: '90', label: 'Last 90 days' },
  { value: '365', label: 'Last year' },
]

const statusColors = {
  published: '#10B981',
  draft: '#F59E0B',
  scheduled: '#3B82F6',
  archived: '#6B7280',
  pending_review: '#8B5CF6',
}

function StatCard({ title, value, subtitle, icon: Icon, iconColor, isLoading }) {
  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-500 dark:text-gray-400">{title}</p>
            {isLoading ? (
              <div className="h-8 w-20 bg-gray-200 dark:bg-gray-700 rounded animate-pulse mt-1" />
            ) : (
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100 mt-1">{value}</p>
            )}
            {subtitle && (
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{subtitle}</p>
            )}
          </div>
          <div className={`h-12 w-12 rounded-lg flex items-center justify-center ${iconColor}`}>
            <Icon className="h-6 w-6 text-white" />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function SimpleBarChart({ data, maxValue }) {
  if (!data || data.length === 0) {
    return (
      <div className="h-40 flex items-center justify-center text-gray-500 dark:text-gray-400">
        No activity data available
      </div>
    )
  }

  return (
    <div className="flex items-end justify-between gap-2 h-40">
      {data.map((item, index) => {
        const height = maxValue > 0 ? (item.count / maxValue) * 100 : 0
        const dateStr = new Date(item.date).toLocaleDateString('en-US', { weekday: 'short' })
        return (
          <div key={index} className="flex-1 flex flex-col items-center">
            <div
              className="w-full bg-primary-500 rounded-t hover:bg-primary-600 transition-colors min-h-[4px]"
              style={{ height: `${Math.max(height, 2)}%` }}
              title={`${item.count} activities`}
            />
            <span className="text-xs text-gray-500 dark:text-gray-400 mt-2">{dateStr}</span>
          </div>
        )
      })}
    </div>
  )
}

function AnalyticsPage() {
  const [period, setPeriod] = useState('30')

  // Fetch dashboard analytics from real API
  const { data: analytics, isLoading, error, refetch } = useQuery({
    queryKey: ['analytics', 'dashboard'],
    queryFn: async () => {
      const response = await analyticsApi.getDashboard()
      return response.data
    },
  })

  // Fetch activity stats based on selected period
  const { data: activityData } = useQuery({
    queryKey: ['analytics', 'activity', period],
    queryFn: async () => {
      const response = await analyticsApi.getActivityStats(parseInt(period))
      return response.data
    },
  })

  const contentStats = analytics?.content || {}
  const userStats = analytics?.users || {}
  const mediaStats = analytics?.media || {}
  const activity = activityData || analytics?.activity || {}

  const dailyActivities = activity?.daily_activities || []
  const maxActivity = Math.max(...dailyActivities.map(d => d.count), 1)

  // Transform content_by_status to array format for display
  const contentByStatus = Object.entries(contentStats.content_by_status || {}).map(([status, count]) => ({
    status: status.charAt(0).toUpperCase() + status.slice(1).replace('_', ' '),
    count,
    color: statusColors[status] || '#6B7280',
  }))

  const totalContent = contentStats.total_content || 0

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <AlertCircle className="h-12 w-12 text-red-500 mb-4" />
        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">Failed to load analytics</h3>
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
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Analytics</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">Monitor your content performance</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
            className="input py-2"
          >
            {periods.map((p) => (
              <option key={p.value} value={p.value}>{p.label}</option>
            ))}
          </select>
          <Button variant="outline" onClick={() => refetch()} disabled={isLoading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Overview stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Total Content"
          value={contentStats.total_content?.toLocaleString() || '0'}
          subtitle={`${contentStats.recent_content_30_days || 0} in last 30 days`}
          icon={FileText}
          iconColor="bg-blue-500"
          isLoading={isLoading}
        />
        <StatCard
          title="Total Users"
          value={userStats.total_users?.toLocaleString() || '0'}
          icon={Users}
          iconColor="bg-green-500"
          isLoading={isLoading}
        />
        <StatCard
          title="Total Media"
          value={mediaStats.total_media?.toLocaleString() || '0'}
          subtitle={`${mediaStats.total_storage_mb || 0} MB used`}
          icon={HardDrive}
          iconColor="bg-purple-500"
          isLoading={isLoading}
        />
        <StatCard
          title="Activities"
          value={activity.total_activities?.toLocaleString() || '0'}
          subtitle={`Last ${period} days`}
          icon={Calendar}
          iconColor="bg-orange-500"
          isLoading={isLoading}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Activity chart */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              Daily Activity
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="h-40 flex items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
              </div>
            ) : (
              <SimpleBarChart data={dailyActivities.slice(-7)} maxValue={maxActivity} />
            )}
          </CardContent>
        </Card>

        {/* Content by status */}
        <Card>
          <CardHeader>
            <CardTitle>Content by Status</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="space-y-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-8 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
                ))}
              </div>
            ) : contentByStatus.length > 0 ? (
              <div className="space-y-4">
                {contentByStatus.map((item) => (
                  <div key={item.status}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm text-gray-700 dark:text-gray-300">{item.status}</span>
                      <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{item.count}</span>
                    </div>
                    <div className="h-2 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all"
                        style={{
                          width: totalContent > 0 ? `${(item.count / totalContent) * 100}%` : '0%',
                          backgroundColor: item.color,
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 dark:text-gray-400 text-center py-4">No content data</p>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Most active users */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Most Active Users
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {isLoading ? (
              <div className="p-6 space-y-4">
                {[1, 2, 3, 4, 5].map((i) => (
                  <div key={i} className="h-10 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
                ))}
              </div>
            ) : (activity.most_active_users_top10?.length || 0) > 0 ? (
              <div className="divide-y divide-gray-200 dark:divide-gray-700">
                {activity.most_active_users_top10.slice(0, 5).map((user, index) => (
                  <div key={user.user_id} className="flex items-center gap-4 px-6 py-4">
                    <span className="text-lg font-bold text-gray-400 w-6">{index + 1}</span>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-gray-900 dark:text-gray-100 truncate">{user.username}</p>
                      <p className="text-sm text-gray-500 dark:text-gray-400">{user.activity_count} activities</p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 dark:text-gray-400 text-center py-8">No activity data</p>
            )}
          </CardContent>
        </Card>

        {/* Activities by action */}
        <Card>
          <CardHeader>
            <CardTitle>Activities by Action</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="space-y-4">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="h-8 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
                ))}
              </div>
            ) : Object.keys(activity.activities_by_action || {}).length > 0 ? (
              <div className="space-y-4">
                {Object.entries(activity.activities_by_action).slice(0, 6).map(([action, count]) => {
                  const totalActivities = activity.total_activities || 1
                  const percentage = Math.round((count / totalActivities) * 100)
                  return (
                    <div key={action}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm text-gray-700 dark:text-gray-300 capitalize">{action.replace('_', ' ')}</span>
                        <span className="text-sm text-gray-500 dark:text-gray-400">
                          {count.toLocaleString()} ({percentage}%)
                        </span>
                      </div>
                      <div className="h-2 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary-500 rounded-full transition-all"
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <p className="text-gray-500 dark:text-gray-400 text-center py-4">No activity data</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Top uploaders */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <HardDrive className="h-5 w-5" />
            Top Media Uploaders
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6 space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-12 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
              ))}
            </div>
          ) : (mediaStats.top_uploaders_top10?.length || 0) > 0 ? (
            <div className="divide-y divide-gray-200 dark:divide-gray-700">
              {mediaStats.top_uploaders_top10.slice(0, 5).map((uploader, index) => (
                <div key={uploader.user_id} className="flex items-center gap-4 px-6 py-4">
                  <span className="text-lg font-bold text-gray-400 w-6">{index + 1}</span>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900 dark:text-gray-100 truncate">{uploader.username}</p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      {uploader.upload_count} files ({Math.round(uploader.total_size_bytes / (1024 * 1024))} MB)
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 dark:text-gray-400 text-center py-8">No upload data</p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default AnalyticsPage
