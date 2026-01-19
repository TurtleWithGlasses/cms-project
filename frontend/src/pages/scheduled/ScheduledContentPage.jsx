import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { contentApi } from '../../services/api'
import { useToast } from '../../components/ui/Toast'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card'
import Button from '../../components/ui/Button'
import {
  Calendar,
  Clock,
  FileText,
  User,
  Edit2,
  Trash2,
  Play,
  Pause,
  Eye,
  ChevronLeft,
  ChevronRight,
  AlertCircle,
} from 'lucide-react'

// Mock data for demo
const mockScheduledContent = [
  {
    id: 1,
    title: 'New Year Product Launch',
    type: 'page',
    author: 'John Doe',
    scheduledFor: '2024-01-20T09:00:00Z',
    status: 'scheduled',
    category: 'Announcements',
  },
  {
    id: 2,
    title: 'Weekly Newsletter #45',
    type: 'post',
    author: 'Sarah Smith',
    scheduledFor: '2024-01-21T10:30:00Z',
    status: 'scheduled',
    category: 'Newsletter',
  },
  {
    id: 3,
    title: 'Feature Update: Dark Mode',
    type: 'post',
    author: 'Mike Johnson',
    scheduledFor: '2024-01-22T14:00:00Z',
    status: 'scheduled',
    category: 'Updates',
  },
  {
    id: 4,
    title: 'Q1 Goals Blog Post',
    type: 'post',
    author: 'Emma Wilson',
    scheduledFor: '2024-01-25T08:00:00Z',
    status: 'scheduled',
    category: 'Blog',
  },
  {
    id: 5,
    title: 'Valentine\'s Day Campaign',
    type: 'page',
    author: 'John Doe',
    scheduledFor: '2024-02-10T00:00:00Z',
    status: 'scheduled',
    category: 'Campaigns',
  },
]

function ScheduledContentPage() {
  const queryClient = useQueryClient()
  const toast = useToast()
  const [currentMonth, setCurrentMonth] = useState(new Date())
  const [selectedDate, setSelectedDate] = useState(null)
  const [view, setView] = useState('calendar') // 'calendar' or 'list'

  // Fetch scheduled content
  const { data: scheduledContent = mockScheduledContent, isLoading } = useQuery({
    queryKey: ['scheduled-content'],
    queryFn: () => contentApi.getAll({ status: 'scheduled' }),
    select: (res) => res.data || mockScheduledContent,
    placeholderData: mockScheduledContent,
  })

  // Publish now mutation
  const publishNowMutation = useMutation({
    mutationFn: (id) => contentApi.publish(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scheduled-content'] })
      toast.success('Content published successfully')
    },
    onError: () => toast.error('Failed to publish content'),
  })

  // Cancel schedule mutation
  const cancelScheduleMutation = useMutation({
    mutationFn: (id) => contentApi.update(id, { scheduled_for: null, status: 'draft' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scheduled-content'] })
      toast.success('Schedule cancelled. Content moved to drafts.')
    },
    onError: () => toast.error('Failed to cancel schedule'),
  })

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const getRelativeTime = (dateString) => {
    const date = new Date(dateString)
    const now = new Date()
    const diff = date - now
    const days = Math.floor(diff / (1000 * 60 * 60 * 24))
    const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))

    if (days > 0) return `in ${days} day${days > 1 ? 's' : ''}`
    if (hours > 0) return `in ${hours} hour${hours > 1 ? 's' : ''}`
    if (diff > 0) return 'soon'
    return 'overdue'
  }

  // Calendar helpers
  const getDaysInMonth = (date) => {
    const year = date.getFullYear()
    const month = date.getMonth()
    const firstDay = new Date(year, month, 1)
    const lastDay = new Date(year, month + 1, 0)
    const daysInMonth = lastDay.getDate()
    const startingDay = firstDay.getDay()

    const days = []
    // Add empty cells for days before the first day of the month
    for (let i = 0; i < startingDay; i++) {
      days.push(null)
    }
    // Add days of the month
    for (let i = 1; i <= daysInMonth; i++) {
      days.push(new Date(year, month, i))
    }
    return days
  }

  const getContentForDate = (date) => {
    if (!date) return []
    return scheduledContent.filter((content) => {
      const schedDate = new Date(content.scheduledFor)
      return (
        schedDate.getFullYear() === date.getFullYear() &&
        schedDate.getMonth() === date.getMonth() &&
        schedDate.getDate() === date.getDate()
      )
    })
  }

  const prevMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1))
  }

  const nextMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1))
  }

  const days = getDaysInMonth(currentMonth)
  const monthName = currentMonth.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })

  const sortedContent = [...scheduledContent].sort(
    (a, b) => new Date(a.scheduledFor) - new Date(b.scheduledFor)
  )

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Scheduled Content</h1>
          <p className="text-gray-500 mt-1">Manage your upcoming publications</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex border border-gray-200 rounded-lg overflow-hidden">
            <button
              onClick={() => setView('calendar')}
              className={`px-4 py-2 text-sm font-medium ${
                view === 'calendar' ? 'bg-primary-100 text-primary-700' : 'text-gray-600 hover:bg-gray-50'
              }`}
            >
              <Calendar className="h-4 w-4" />
            </button>
            <button
              onClick={() => setView('list')}
              className={`px-4 py-2 text-sm font-medium ${
                view === 'list' ? 'bg-primary-100 text-primary-700' : 'text-gray-600 hover:bg-gray-50'
              }`}
            >
              <FileText className="h-4 w-4" />
            </button>
          </div>
          <Link to="/content/new">
            <Button>Schedule New Content</Button>
          </Link>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-4 flex items-center gap-4">
            <div className="h-12 w-12 bg-blue-100 rounded-lg flex items-center justify-center">
              <Calendar className="h-6 w-6 text-blue-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{scheduledContent.length}</p>
              <p className="text-sm text-gray-500">Total Scheduled</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center gap-4">
            <div className="h-12 w-12 bg-green-100 rounded-lg flex items-center justify-center">
              <Clock className="h-6 w-6 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">
                {scheduledContent.filter((c) => {
                  const diff = new Date(c.scheduledFor) - new Date()
                  return diff > 0 && diff < 7 * 24 * 60 * 60 * 1000
                }).length}
              </p>
              <p className="text-sm text-gray-500">This Week</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center gap-4">
            <div className="h-12 w-12 bg-yellow-100 rounded-lg flex items-center justify-center">
              <AlertCircle className="h-6 w-6 text-yellow-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">
                {scheduledContent.filter((c) => {
                  const diff = new Date(c.scheduledFor) - new Date()
                  return diff > 0 && diff < 24 * 60 * 60 * 1000
                }).length}
              </p>
              <p className="text-sm text-gray-500">Next 24 Hours</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {view === 'calendar' ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Calendar */}
          <Card className="lg:col-span-2">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>{monthName}</CardTitle>
                <div className="flex items-center gap-2">
                  <button
                    onClick={prevMonth}
                    className="p-2 hover:bg-gray-100 rounded-lg"
                  >
                    <ChevronLeft className="h-5 w-5" />
                  </button>
                  <button
                    onClick={nextMonth}
                    className="p-2 hover:bg-gray-100 rounded-lg"
                  >
                    <ChevronRight className="h-5 w-5" />
                  </button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-7 gap-1">
                {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((day) => (
                  <div key={day} className="text-center text-sm font-medium text-gray-500 py-2">
                    {day}
                  </div>
                ))}
                {days.map((day, index) => {
                  const contentForDay = day ? getContentForDate(day) : []
                  const isToday = day && day.toDateString() === new Date().toDateString()
                  const isSelected = selectedDate && day && day.toDateString() === selectedDate.toDateString()

                  return (
                    <button
                      key={index}
                      onClick={() => day && setSelectedDate(day)}
                      disabled={!day}
                      className={`min-h-[80px] p-1 border border-gray-100 rounded-lg text-left transition-colors ${
                        !day ? 'bg-gray-50 cursor-default' :
                        isSelected ? 'bg-primary-50 border-primary-200' :
                        isToday ? 'bg-blue-50 border-blue-200' :
                        'hover:bg-gray-50'
                      }`}
                    >
                      {day && (
                        <>
                          <span className={`text-sm font-medium ${
                            isToday ? 'text-blue-600' : 'text-gray-700'
                          }`}>
                            {day.getDate()}
                          </span>
                          <div className="space-y-1 mt-1">
                            {contentForDay.slice(0, 2).map((content) => (
                              <div
                                key={content.id}
                                className="text-xs bg-primary-100 text-primary-700 px-1 py-0.5 rounded truncate"
                              >
                                {content.title}
                              </div>
                            ))}
                            {contentForDay.length > 2 && (
                              <div className="text-xs text-gray-500">
                                +{contentForDay.length - 2} more
                              </div>
                            )}
                          </div>
                        </>
                      )}
                    </button>
                  )
                })}
              </div>
            </CardContent>
          </Card>

          {/* Selected date details */}
          <Card>
            <CardHeader>
              <CardTitle>
                {selectedDate
                  ? selectedDate.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })
                  : 'Select a Date'}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {selectedDate ? (
                getContentForDate(selectedDate).length > 0 ? (
                  <div className="space-y-3">
                    {getContentForDate(selectedDate).map((content) => (
                      <div key={content.id} className="p-3 border border-gray-200 rounded-lg">
                        <h4 className="font-medium text-gray-900">{content.title}</h4>
                        <div className="text-sm text-gray-500 mt-1">
                          <Clock className="h-3 w-3 inline mr-1" />
                          {new Date(content.scheduledFor).toLocaleTimeString('en-US', {
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </div>
                        <div className="flex gap-2 mt-3">
                          <Link to={`/content/${content.id}`}>
                            <Button variant="outline" size="sm">
                              <Edit2 className="h-3 w-3 mr-1" />
                              Edit
                            </Button>
                          </Link>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => publishNowMutation.mutate(content.id)}
                          >
                            <Play className="h-3 w-3 mr-1" />
                            Publish Now
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    <Calendar className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                    <p>No content scheduled for this date</p>
                  </div>
                )
              ) : (
                <div className="text-center py-8 text-gray-500">
                  <Calendar className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                  <p>Click on a date to see scheduled content</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      ) : (
        /* List view */
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5" />
              Upcoming Publications
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {sortedContent.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                <Calendar className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                <p>No scheduled content</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-200">
                {sortedContent.map((content) => (
                  <div key={content.id} className="px-6 py-4 flex items-center justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <FileText className="h-4 w-4 text-gray-400" />
                        <h3 className="font-medium text-gray-900 truncate">{content.title}</h3>
                        <span className="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded">
                          {content.type}
                        </span>
                      </div>
                      <div className="flex items-center gap-4 mt-1 text-sm text-gray-500">
                        <span className="flex items-center gap-1">
                          <Calendar className="h-3 w-3" />
                          {formatDate(content.scheduledFor)}
                        </span>
                        <span className="flex items-center gap-1">
                          <User className="h-3 w-3" />
                          {content.author}
                        </span>
                        <span className="text-primary-600 font-medium">
                          {getRelativeTime(content.scheduledFor)}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Link to={`/content/${content.id}`}>
                        <Button variant="outline" size="sm">
                          <Edit2 className="h-4 w-4" />
                        </Button>
                      </Link>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => publishNowMutation.mutate(content.id)}
                      >
                        <Play className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => cancelScheduleMutation.mutate(content.id)}
                        className="text-red-600 hover:text-red-700"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}

export default ScheduledContentPage
