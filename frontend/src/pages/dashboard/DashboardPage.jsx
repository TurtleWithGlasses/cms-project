import { useQuery } from '@tanstack/react-query'
import { dashboardApi } from '../../services/api'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card'
import { SkeletonDashboard } from '../../components/ui/Skeleton'
import {
  FileText,
  Users,
  MessageSquare,
  TrendingUp,
  Clock,
  CheckCircle,
  AlertCircle,
  Activity,
  RefreshCw,
} from 'lucide-react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
} from 'recharts'

function StatCard({ title, value, change, icon: Icon, iconColor = 'text-primary-600', bgColor = 'bg-primary-50', darkBgColor = 'dark:bg-primary-900/30' }) {
  const isPositive = change >= 0

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm font-medium text-gray-500 dark:text-gray-400">{title}</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">{value}</p>
            {change !== undefined && (
              <p className={`text-sm mt-1 ${isPositive ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                {isPositive ? '+' : ''}{change}% from last period
              </p>
            )}
          </div>
          <div className={`p-3 rounded-lg ${bgColor} ${darkBgColor}`}>
            <Icon className={`h-6 w-6 ${iconColor}`} />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function DashboardPage() {
  const {
    data: summary,
    isLoading: summaryLoading,
    error: summaryError,
    refetch: refetchSummary,
  } = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: () => dashboardApi.getSummary(30),
    select: (res) => res.data,
  })

  const {
    data: activity,
    isLoading: activityLoading,
    error: activityError,
    refetch: refetchActivity,
  } = useQuery({
    queryKey: ['my-activity'],
    queryFn: () => dashboardApi.getMyActivity(7),
    select: (res) => res.data,
  })

  const isLoading = summaryLoading || activityLoading
  const hasError = summaryError || activityError

  const handleRetry = () => {
    if (summaryError) refetchSummary()
    if (activityError) refetchActivity()
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">Overview of your CMS performance</p>
        </div>
        <SkeletonDashboard />
      </div>
    )
  }

  if (hasError) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
        <AlertCircle className="h-12 w-12 text-red-500" />
        <div className="text-center">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Failed to load dashboard</h2>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            {summaryError?.message || activityError?.message || 'An error occurred while loading the dashboard data.'}
          </p>
        </div>
        <button
          onClick={handleRetry}
          className="btn btn-secondary flex items-center gap-2"
        >
          <RefreshCw className="h-4 w-4" />
          Retry
        </button>
      </div>
    )
  }

  const { content, users, comments, activity: activityKpis } = summary || {}

  // Prepare chart data
  const dailyActivityData = activityKpis?.daily_activity || []

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">Overview of your CMS performance</p>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Total Content"
          value={content?.total_content || 0}
          change={content?.growth_rate_percent}
          icon={FileText}
        />
        <StatCard
          title="Published"
          value={content?.published_content || 0}
          icon={CheckCircle}
          iconColor="text-green-600 dark:text-green-400"
          bgColor="bg-green-50"
          darkBgColor="dark:bg-green-900/30"
        />
        <StatCard
          title="Total Users"
          value={users?.total_users || 0}
          icon={Users}
          iconColor="text-blue-600 dark:text-blue-400"
          bgColor="bg-blue-50"
          darkBgColor="dark:bg-blue-900/30"
        />
        <StatCard
          title="Pending Moderation"
          value={comments?.pending_moderation || 0}
          icon={MessageSquare}
          iconColor="text-orange-600 dark:text-orange-400"
          bgColor="bg-orange-50"
          darkBgColor="dark:bg-orange-900/30"
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Activity chart */}
        <Card>
          <CardHeader>
            <CardTitle>Daily Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              {dailyActivityData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={dailyActivityData}>
                    <CartesianGrid strokeDasharray="3 3" className="dark:opacity-30" />
                    <XAxis
                      dataKey="date"
                      tickFormatter={(value) => new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                      className="dark:fill-gray-400"
                    />
                    <YAxis className="dark:fill-gray-400" />
                    <Tooltip
                      labelFormatter={(value) => new Date(value).toLocaleDateString()}
                      contentStyle={{ backgroundColor: 'var(--tooltip-bg, #fff)', borderColor: 'var(--tooltip-border, #e5e7eb)' }}
                    />
                    <Area
                      type="monotone"
                      dataKey="count"
                      stroke="#3b82f6"
                      fill="#93c5fd"
                      name="Actions"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
                  No activity data available
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Content by status */}
        <Card>
          <CardHeader>
            <CardTitle>Content by Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              {content?.content_by_status && Object.keys(content.content_by_status).length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={Object.entries(content.content_by_status).map(([name, value]) => ({
                      name: name.charAt(0).toUpperCase() + name.slice(1),
                      value,
                    }))}
                  >
                    <CartesianGrid strokeDasharray="3 3" className="dark:opacity-30" />
                    <XAxis dataKey="name" className="dark:fill-gray-400" />
                    <YAxis className="dark:fill-gray-400" />
                    <Tooltip
                      contentStyle={{ backgroundColor: 'var(--tooltip-bg, #fff)', borderColor: 'var(--tooltip-border, #e5e7eb)' }}
                    />
                    <Bar dataKey="value" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
                  No content data available
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Bottom row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Quick stats */}
        <Card>
          <CardHeader>
            <CardTitle>Quick Stats</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-yellow-50 dark:bg-yellow-900/30 rounded-lg">
                  <Clock className="h-4 w-4 text-yellow-600 dark:text-yellow-400" />
                </div>
                <span className="text-sm text-gray-600 dark:text-gray-400">Stale Drafts</span>
              </div>
              <span className="font-semibold text-gray-900 dark:text-white">{content?.stale_drafts || 0}</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-50 dark:bg-green-900/30 rounded-lg">
                  <Activity className="h-4 w-4 text-green-600 dark:text-green-400" />
                </div>
                <span className="text-sm text-gray-600 dark:text-gray-400">Active Sessions</span>
              </div>
              <span className="font-semibold text-gray-900 dark:text-white">{users?.active_sessions || 0}</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-50 dark:bg-blue-900/30 rounded-lg">
                  <TrendingUp className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                </div>
                <span className="text-sm text-gray-600 dark:text-gray-400">2FA Adoption</span>
              </div>
              <span className="font-semibold text-gray-900 dark:text-white">{users?.two_fa_adoption_percent || 0}%</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-50 dark:bg-purple-900/30 rounded-lg">
                  <Users className="h-4 w-4 text-purple-600 dark:text-purple-400" />
                </div>
                <span className="text-sm text-gray-600 dark:text-gray-400">New Users (30d)</span>
              </div>
              <span className="font-semibold text-gray-900 dark:text-white">{users?.new_users_this_period || 0}</span>
            </div>
          </CardContent>
        </Card>

        {/* Recent activity */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            {activity && activity.length > 0 ? (
              <div className="space-y-3">
                {activity.slice(0, 5).map((item) => (
                  <div key={item.id} className="flex items-start gap-3 p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                    <div className="p-2 bg-gray-100 dark:bg-gray-700 rounded-lg">
                      <Activity className="h-4 w-4 text-gray-600 dark:text-gray-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                        {item.action}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {new Date(item.created_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 dark:text-gray-400 text-center py-8">No recent activity</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default DashboardPage
