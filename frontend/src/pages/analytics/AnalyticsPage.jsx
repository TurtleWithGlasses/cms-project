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
  Clock,
  Calendar,
  Download,
  RefreshCw,
  ArrowUpRight,
  ArrowDownRight,
} from 'lucide-react'

const periods = [
  { value: '7', label: 'Last 7 days' },
  { value: '30', label: 'Last 30 days' },
  { value: '90', label: 'Last 90 days' },
  { value: '365', label: 'Last year' },
]

// Mock data for demo
const mockAnalytics = {
  overview: {
    totalViews: 125840,
    viewsChange: 12.5,
    totalContent: 342,
    contentChange: 8.2,
    activeUsers: 1250,
    usersChange: -2.3,
    avgReadTime: '4:32',
    readTimeChange: 5.1,
  },
  topContent: [
    { id: 1, title: 'Getting Started with React', views: 12500, trend: 15.2 },
    { id: 2, title: 'Understanding TypeScript', views: 9800, trend: 8.7 },
    { id: 3, title: 'CSS Grid Layout Guide', views: 8200, trend: -3.2 },
    { id: 4, title: 'Node.js Best Practices', views: 7500, trend: 22.1 },
    { id: 5, title: 'Database Optimization Tips', views: 6300, trend: 4.5 },
  ],
  trafficSources: [
    { source: 'Organic Search', visits: 45200, percentage: 42 },
    { source: 'Direct', visits: 28900, percentage: 27 },
    { source: 'Social Media', visits: 18500, percentage: 17 },
    { source: 'Referral', visits: 10200, percentage: 9 },
    { source: 'Email', visits: 5400, percentage: 5 },
  ],
  contentByStatus: [
    { status: 'Published', count: 245, color: '#10B981' },
    { status: 'Draft', count: 67, color: '#F59E0B' },
    { status: 'Scheduled', count: 18, color: '#3B82F6' },
    { status: 'Under Review', count: 12, color: '#8B5CF6' },
  ],
  recentActivity: [
    { action: 'Published', title: 'New Feature Announcement', time: '2 hours ago', user: 'John D.' },
    { action: 'Edited', title: 'API Documentation', time: '4 hours ago', user: 'Sarah M.' },
    { action: 'Created', title: 'Q1 Report Draft', time: '6 hours ago', user: 'Mike R.' },
    { action: 'Published', title: 'Security Update Guide', time: '1 day ago', user: 'Emma L.' },
    { action: 'Deleted', title: 'Outdated Policy Page', time: '1 day ago', user: 'Admin' },
  ],
  dailyViews: [
    { date: 'Mon', views: 4200 },
    { date: 'Tue', views: 5100 },
    { date: 'Wed', views: 4800 },
    { date: 'Thu', views: 6200 },
    { date: 'Fri', views: 5500 },
    { date: 'Sat', views: 3200 },
    { date: 'Sun', views: 2800 },
  ],
}

function StatCard({ title, value, change, icon: Icon, iconColor }) {
  const isPositive = change >= 0
  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-500">{title}</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
            <div className={`flex items-center mt-2 text-sm ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
              {isPositive ? (
                <ArrowUpRight className="h-4 w-4 mr-1" />
              ) : (
                <ArrowDownRight className="h-4 w-4 mr-1" />
              )}
              <span>{Math.abs(change)}% from last period</span>
            </div>
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
  return (
    <div className="flex items-end justify-between gap-2 h-40">
      {data.map((item, index) => {
        const height = (item.views / maxValue) * 100
        return (
          <div key={index} className="flex-1 flex flex-col items-center">
            <div
              className="w-full bg-primary-500 rounded-t hover:bg-primary-600 transition-colors"
              style={{ height: `${height}%` }}
              title={`${item.views.toLocaleString()} views`}
            />
            <span className="text-xs text-gray-500 mt-2">{item.date}</span>
          </div>
        )
      })}
    </div>
  )
}

function AnalyticsPage() {
  const [period, setPeriod] = useState('30')

  // In a real app, this would fetch from API
  const { data: analytics = mockAnalytics, isLoading, refetch } = useQuery({
    queryKey: ['analytics', period],
    queryFn: () => analyticsApi.getOverview({ period_days: parseInt(period) }),
    select: (res) => res.data || mockAnalytics,
    placeholderData: mockAnalytics,
  })

  const maxViews = Math.max(...analytics.dailyViews.map((d) => d.views))

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
          <p className="text-gray-500 mt-1">Monitor your content performance</p>
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
          <Button variant="outline" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          <Button variant="outline">
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
        </div>
      </div>

      {/* Overview stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Total Views"
          value={analytics.overview.totalViews.toLocaleString()}
          change={analytics.overview.viewsChange}
          icon={Eye}
          iconColor="bg-blue-500"
        />
        <StatCard
          title="Total Content"
          value={analytics.overview.totalContent.toLocaleString()}
          change={analytics.overview.contentChange}
          icon={FileText}
          iconColor="bg-green-500"
        />
        <StatCard
          title="Active Users"
          value={analytics.overview.activeUsers.toLocaleString()}
          change={analytics.overview.usersChange}
          icon={Users}
          iconColor="bg-purple-500"
        />
        <StatCard
          title="Avg. Read Time"
          value={analytics.overview.avgReadTime}
          change={analytics.overview.readTimeChange}
          icon={Clock}
          iconColor="bg-orange-500"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Views chart */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              Daily Views
            </CardTitle>
          </CardHeader>
          <CardContent>
            <SimpleBarChart data={analytics.dailyViews} maxValue={maxViews} />
          </CardContent>
        </Card>

        {/* Content by status */}
        <Card>
          <CardHeader>
            <CardTitle>Content by Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {analytics.contentByStatus.map((item) => (
                <div key={item.status}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-gray-700">{item.status}</span>
                    <span className="text-sm font-medium text-gray-900">{item.count}</span>
                  </div>
                  <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${(item.count / analytics.overview.totalContent) * 100}%`,
                        backgroundColor: item.color,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top content */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Top Performing Content
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-gray-200">
              {analytics.topContent.map((content, index) => (
                <div key={content.id} className="flex items-center gap-4 px-6 py-4">
                  <span className="text-lg font-bold text-gray-400 w-6">{index + 1}</span>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900 truncate">{content.title}</p>
                    <p className="text-sm text-gray-500">{content.views.toLocaleString()} views</p>
                  </div>
                  <div className={`flex items-center text-sm ${content.trend >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {content.trend >= 0 ? (
                      <TrendingUp className="h-4 w-4 mr-1" />
                    ) : (
                      <TrendingDown className="h-4 w-4 mr-1" />
                    )}
                    {Math.abs(content.trend)}%
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Traffic sources */}
        <Card>
          <CardHeader>
            <CardTitle>Traffic Sources</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {analytics.trafficSources.map((source) => (
                <div key={source.source}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-gray-700">{source.source}</span>
                    <span className="text-sm text-gray-500">
                      {source.visits.toLocaleString()} ({source.percentage}%)
                    </span>
                  </div>
                  <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary-500 rounded-full transition-all"
                      style={{ width: `${source.percentage}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent activity */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calendar className="h-5 w-5" />
            Recent Activity
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="divide-y divide-gray-200">
            {analytics.recentActivity.map((activity, index) => (
              <div key={index} className="flex items-center gap-4 px-6 py-4">
                <div className={`px-2 py-1 rounded text-xs font-medium ${
                  activity.action === 'Published' ? 'bg-green-100 text-green-700' :
                  activity.action === 'Edited' ? 'bg-blue-100 text-blue-700' :
                  activity.action === 'Created' ? 'bg-purple-100 text-purple-700' :
                  'bg-red-100 text-red-700'
                }`}>
                  {activity.action}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-gray-900 truncate">{activity.title}</p>
                  <p className="text-sm text-gray-500">by {activity.user}</p>
                </div>
                <span className="text-sm text-gray-400">{activity.time}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default AnalyticsPage
