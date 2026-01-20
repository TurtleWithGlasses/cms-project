import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Mail,
  Edit2,
  Eye,
  Save,
  Send,
  Code,
  FileText,
  Search,
  ChevronRight,
  Check,
  X,
  RefreshCw,
  Copy,
  Variable,
} from 'lucide-react'
import { useToast } from '../../components/ui/Toast'

// Mock Email Templates API
const emailTemplatesApi = {
  getAll: () => Promise.resolve([
    {
      id: 'welcome',
      name: 'Welcome Email',
      description: 'Sent when a new user registers',
      subject: 'Welcome to {{site_name}}!',
      category: 'authentication',
      lastModified: '2024-01-10T14:30:00Z',
      isActive: true,
    },
    {
      id: 'password-reset',
      name: 'Password Reset',
      description: 'Sent when a user requests password reset',
      subject: 'Reset your {{site_name}} password',
      category: 'authentication',
      lastModified: '2024-01-08T09:15:00Z',
      isActive: true,
    },
    {
      id: 'email-verification',
      name: 'Email Verification',
      description: 'Sent to verify email address',
      subject: 'Verify your email address',
      category: 'authentication',
      lastModified: '2024-01-05T11:00:00Z',
      isActive: true,
    },
    {
      id: 'comment-notification',
      name: 'New Comment',
      description: 'Notify author of new comment',
      subject: 'New comment on "{{post_title}}"',
      category: 'notifications',
      lastModified: '2024-01-12T16:45:00Z',
      isActive: true,
    },
    {
      id: 'content-published',
      name: 'Content Published',
      description: 'Notify author when content is published',
      subject: 'Your content "{{content_title}}" has been published',
      category: 'notifications',
      lastModified: '2024-01-11T10:30:00Z',
      isActive: false,
    },
    {
      id: 'team-invitation',
      name: 'Team Invitation',
      description: 'Invite users to join a team',
      subject: 'You\'ve been invited to join {{team_name}}',
      category: 'teams',
      lastModified: '2024-01-09T13:20:00Z',
      isActive: true,
    },
    {
      id: 'workflow-approval',
      name: 'Workflow Approval Request',
      description: 'Request content approval',
      subject: 'Content approval requested: "{{content_title}}"',
      category: 'workflow',
      lastModified: '2024-01-07T08:00:00Z',
      isActive: true,
    },
    {
      id: 'workflow-approved',
      name: 'Content Approved',
      description: 'Notify when content is approved',
      subject: 'Your content "{{content_title}}" has been approved',
      category: 'workflow',
      lastModified: '2024-01-07T08:00:00Z',
      isActive: true,
    },
  ]),
  getById: (id) => Promise.resolve({
    id,
    name: 'Welcome Email',
    subject: 'Welcome to {{site_name}}!',
    htmlContent: `<!DOCTYPE html>
<html>
<head>
  <style>
    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
    .container { max-width: 600px; margin: 0 auto; padding: 20px; }
    .header { background: #3b82f6; color: white; padding: 20px; text-align: center; }
    .content { padding: 30px 20px; background: #f9fafb; }
    .button { display: inline-block; background: #3b82f6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; }
    .footer { padding: 20px; text-align: center; color: #6b7280; font-size: 12px; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>Welcome to {{site_name}}!</h1>
    </div>
    <div class="content">
      <p>Hi {{user_name}},</p>
      <p>Thank you for joining {{site_name}}! We're excited to have you on board.</p>
      <p>To get started, click the button below to verify your email address:</p>
      <p style="text-align: center; margin: 30px 0;">
        <a href="{{verification_url}}" class="button">Verify Email Address</a>
      </p>
      <p>If you didn't create an account, you can safely ignore this email.</p>
      <p>Best regards,<br>The {{site_name}} Team</p>
    </div>
    <div class="footer">
      <p>© {{current_year}} {{site_name}}. All rights reserved.</p>
      <p><a href="{{unsubscribe_url}}">Unsubscribe</a></p>
    </div>
  </div>
</body>
</html>`,
    textContent: `Welcome to {{site_name}}!

Hi {{user_name}},

Thank you for joining {{site_name}}! We're excited to have you on board.

To get started, verify your email address by visiting:
{{verification_url}}

If you didn't create an account, you can safely ignore this email.

Best regards,
The {{site_name}} Team`,
    variables: [
      { name: 'site_name', description: 'Your website name' },
      { name: 'user_name', description: 'Recipient\'s name' },
      { name: 'user_email', description: 'Recipient\'s email' },
      { name: 'verification_url', description: 'Email verification link' },
      { name: 'current_year', description: 'Current year' },
      { name: 'unsubscribe_url', description: 'Unsubscribe link' },
    ],
  }),
  update: (id, data) => Promise.resolve({ success: true }),
  sendTest: (id, email) => Promise.resolve({ success: true }),
  resetToDefault: (id) => Promise.resolve({ success: true }),
}

const categories = [
  { id: 'all', name: 'All Templates' },
  { id: 'authentication', name: 'Authentication' },
  { id: 'notifications', name: 'Notifications' },
  { id: 'teams', name: 'Teams' },
  { id: 'workflow', name: 'Workflow' },
]

function EmailTemplatesPage() {
  const [selectedTemplate, setSelectedTemplate] = useState(null)
  const [activeCategory, setActiveCategory] = useState('all')
  const [searchTerm, setSearchTerm] = useState('')
  const [viewMode, setViewMode] = useState('visual') // 'visual' | 'html' | 'text'
  const [showTestModal, setShowTestModal] = useState(false)
  const [testEmail, setTestEmail] = useState('')
  const [editedContent, setEditedContent] = useState(null)

  const { toast } = useToast()
  const queryClient = useQueryClient()

  const { data: templates, isLoading: loadingTemplates } = useQuery({
    queryKey: ['email-templates'],
    queryFn: emailTemplatesApi.getAll,
  })

  const { data: templateDetail, isLoading: loadingDetail } = useQuery({
    queryKey: ['email-template', selectedTemplate],
    queryFn: () => emailTemplatesApi.getById(selectedTemplate),
    enabled: !!selectedTemplate,
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }) => emailTemplatesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['email-templates'])
      queryClient.invalidateQueries(['email-template', selectedTemplate])
      toast({ title: 'Template saved', variant: 'success' })
    },
  })

  const sendTestMutation = useMutation({
    mutationFn: ({ id, email }) => emailTemplatesApi.sendTest(id, email),
    onSuccess: () => {
      setShowTestModal(false)
      setTestEmail('')
      toast({ title: 'Test email sent', description: `Check ${testEmail}`, variant: 'success' })
    },
  })

  const resetMutation = useMutation({
    mutationFn: emailTemplatesApi.resetToDefault,
    onSuccess: () => {
      queryClient.invalidateQueries(['email-template', selectedTemplate])
      setEditedContent(null)
      toast({ title: 'Template reset to default', variant: 'success' })
    },
  })

  const filteredTemplates = templates?.filter((template) => {
    const matchesCategory = activeCategory === 'all' || template.category === activeCategory
    const matchesSearch = !searchTerm ||
      template.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      template.description.toLowerCase().includes(searchTerm.toLowerCase())
    return matchesCategory && matchesSearch
  })

  const currentContent = editedContent || templateDetail

  const handleSave = () => {
    if (currentContent) {
      updateMutation.mutate({ id: selectedTemplate, data: currentContent })
    }
  }

  const copyVariable = (variable) => {
    navigator.clipboard.writeText(`{{${variable}}}`)
    toast({ title: 'Variable copied', variant: 'success' })
  }

  if (loadingTemplates) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Email Templates</h1>
        <p className="text-gray-600 mt-1">Customize the emails sent from your site</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Templates List */}
        <div className="lg:col-span-1 space-y-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search templates..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="input pl-10"
            />
          </div>

          {/* Categories */}
          <div className="flex flex-wrap gap-2">
            {categories.map((category) => (
              <button
                key={category.id}
                onClick={() => setActiveCategory(category.id)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  activeCategory === category.id
                    ? 'bg-primary-100 text-primary-700'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {category.name}
              </button>
            ))}
          </div>

          {/* Templates */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 divide-y divide-gray-100">
            {filteredTemplates?.map((template) => (
              <button
                key={template.id}
                onClick={() => {
                  setSelectedTemplate(template.id)
                  setEditedContent(null)
                }}
                className={`w-full p-4 text-left hover:bg-gray-50 transition-colors ${
                  selectedTemplate === template.id ? 'bg-primary-50' : ''
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`h-10 w-10 rounded-lg flex items-center justify-center ${
                      template.isActive ? 'bg-primary-100' : 'bg-gray-100'
                    }`}>
                      <Mail className={`h-5 w-5 ${template.isActive ? 'text-primary-600' : 'text-gray-400'}`} />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-gray-900">{template.name}</span>
                        {!template.isActive && (
                          <span className="text-xs bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">
                            Disabled
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-500 truncate max-w-[200px]">
                        {template.description}
                      </p>
                    </div>
                  </div>
                  <ChevronRight className="h-5 w-5 text-gray-400" />
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Template Editor */}
        <div className="lg:col-span-2">
          {selectedTemplate && templateDetail ? (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200">
              {/* Editor Header */}
              <div className="p-4 border-b border-gray-200">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900">{templateDetail.name}</h2>
                    <p className="text-sm text-gray-500">{templateDetail.subject}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setShowTestModal(true)}
                      className="btn btn-secondary"
                    >
                      <Send className="h-4 w-4 mr-2" />
                      Send Test
                    </button>
                    <button
                      onClick={handleSave}
                      disabled={updateMutation.isPending}
                      className="btn btn-primary"
                    >
                      <Save className="h-4 w-4 mr-2" />
                      {updateMutation.isPending ? 'Saving...' : 'Save'}
                    </button>
                  </div>
                </div>

                {/* Subject Line */}
                <div className="mt-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Subject Line
                  </label>
                  <input
                    type="text"
                    value={currentContent?.subject || ''}
                    onChange={(e) => setEditedContent({ ...currentContent, subject: e.target.value })}
                    className="input"
                  />
                </div>

                {/* View Mode Tabs */}
                <div className="flex items-center gap-1 mt-4 p-1 bg-gray-100 rounded-lg w-fit">
                  {[
                    { id: 'visual', label: 'Preview', icon: Eye },
                    { id: 'html', label: 'HTML', icon: Code },
                    { id: 'text', label: 'Plain Text', icon: FileText },
                  ].map((mode) => (
                    <button
                      key={mode.id}
                      onClick={() => setViewMode(mode.id)}
                      className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                        viewMode === mode.id
                          ? 'bg-white text-gray-900 shadow-sm'
                          : 'text-gray-600 hover:text-gray-900'
                      }`}
                    >
                      <mode.icon className="h-4 w-4" />
                      {mode.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Editor Content */}
              <div className="grid grid-cols-3">
                <div className="col-span-2 border-r border-gray-200">
                  {loadingDetail ? (
                    <div className="flex items-center justify-center h-96">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
                    </div>
                  ) : viewMode === 'visual' ? (
                    <div className="p-4">
                      <div className="border border-gray-200 rounded-lg overflow-hidden">
                        <iframe
                          srcDoc={currentContent?.htmlContent}
                          className="w-full h-96"
                          title="Email Preview"
                        />
                      </div>
                    </div>
                  ) : viewMode === 'html' ? (
                    <div className="p-4">
                      <textarea
                        value={currentContent?.htmlContent || ''}
                        onChange={(e) => setEditedContent({ ...currentContent, htmlContent: e.target.value })}
                        className="w-full h-96 font-mono text-sm p-4 border border-gray-200 rounded-lg resize-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        placeholder="HTML content..."
                      />
                    </div>
                  ) : (
                    <div className="p-4">
                      <textarea
                        value={currentContent?.textContent || ''}
                        onChange={(e) => setEditedContent({ ...currentContent, textContent: e.target.value })}
                        className="w-full h-96 font-mono text-sm p-4 border border-gray-200 rounded-lg resize-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        placeholder="Plain text content..."
                      />
                    </div>
                  )}
                </div>

                {/* Variables Panel */}
                <div className="p-4">
                  <div className="flex items-center gap-2 mb-4">
                    <Variable className="h-5 w-5 text-gray-400" />
                    <h3 className="font-medium text-gray-900">Available Variables</h3>
                  </div>
                  <div className="space-y-2">
                    {templateDetail.variables?.map((variable) => (
                      <button
                        key={variable.name}
                        onClick={() => copyVariable(variable.name)}
                        className="w-full flex items-center justify-between p-2 rounded-lg hover:bg-gray-50 text-left group"
                      >
                        <div>
                          <code className="text-sm text-primary-600 font-mono">
                            {`{{${variable.name}}}`}
                          </code>
                          <p className="text-xs text-gray-500 mt-0.5">{variable.description}</p>
                        </div>
                        <Copy className="h-4 w-4 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                      </button>
                    ))}
                  </div>

                  <hr className="my-4" />

                  <button
                    onClick={() => resetMutation.mutate(selectedTemplate)}
                    disabled={resetMutation.isPending}
                    className="w-full btn btn-secondary text-sm"
                  >
                    <RefreshCw className={`h-4 w-4 mr-2 ${resetMutation.isPending ? 'animate-spin' : ''}`} />
                    Reset to Default
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
              <Mail className="h-12 w-12 text-gray-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">Select a Template</h3>
              <p className="text-gray-500">
                Choose a template from the list to view and edit its content
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Send Test Modal */}
      {showTestModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4">
            <div className="fixed inset-0 bg-black/50" onClick={() => setShowTestModal(false)} />
            <div className="relative bg-white rounded-xl shadow-xl max-w-md w-full p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Send Test Email</h3>
              <p className="text-gray-600 mb-4">
                Send a test version of this email to check how it looks in real email clients.
              </p>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Email Address
                </label>
                <input
                  type="email"
                  value={testEmail}
                  onChange={(e) => setTestEmail(e.target.value)}
                  className="input"
                  placeholder="you@example.com"
                />
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowTestModal(false)}
                  className="btn btn-secondary flex-1"
                >
                  Cancel
                </button>
                <button
                  onClick={() => sendTestMutation.mutate({ id: selectedTemplate, email: testEmail })}
                  disabled={!testEmail || sendTestMutation.isPending}
                  className="btn btn-primary flex-1"
                >
                  {sendTestMutation.isPending ? 'Sending...' : 'Send Test'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default EmailTemplatesPage
