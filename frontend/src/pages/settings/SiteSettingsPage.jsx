import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Globe,
  Upload,
  Save,
  Image,
  Link,
  Mail,
  Clock,
  MapPin,
  Trash2,
  Eye,
  AlertCircle,
} from 'lucide-react'
import { useToast } from '../../components/ui/Toast'

// Mock Site Settings API
const siteSettingsApi = {
  get: () => Promise.resolve({
    general: {
      siteName: 'My CMS Website',
      tagline: 'A modern content management system',
      siteUrl: 'https://example.com',
      adminEmail: 'admin@example.com',
      timezone: 'America/New_York',
      dateFormat: 'MMMM d, yyyy',
      timeFormat: 'h:mm a',
    },
    branding: {
      logo: null,
      favicon: null,
      primaryColor: '#3b82f6',
      secondaryColor: '#64748b',
    },
    social: {
      facebook: '',
      twitter: '',
      instagram: '',
      linkedin: '',
      youtube: '',
    },
    advanced: {
      maintenanceMode: false,
      maintenanceMessage: 'We are currently performing scheduled maintenance. Please check back soon.',
      allowRegistration: true,
      requireEmailVerification: true,
      defaultUserRole: 'subscriber',
    },
  }),
  update: (data) => Promise.resolve(data),
  uploadLogo: (file) => Promise.resolve({ url: '/uploads/logo.png' }),
  uploadFavicon: (file) => Promise.resolve({ url: '/uploads/favicon.ico' }),
}

const timezones = [
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'Europe/London',
  'Europe/Paris',
  'Europe/Berlin',
  'Asia/Tokyo',
  'Asia/Shanghai',
  'Asia/Dubai',
  'Australia/Sydney',
  'Pacific/Auckland',
]

const dateFormats = [
  { value: 'MMMM d, yyyy', label: 'January 1, 2024' },
  { value: 'MMM d, yyyy', label: 'Jan 1, 2024' },
  { value: 'MM/dd/yyyy', label: '01/01/2024' },
  { value: 'dd/MM/yyyy', label: '01/01/2024 (EU)' },
  { value: 'yyyy-MM-dd', label: '2024-01-01 (ISO)' },
]

const timeFormats = [
  { value: 'h:mm a', label: '1:30 PM' },
  { value: 'HH:mm', label: '13:30' },
]

function SiteSettingsPage() {
  const { toast } = useToast()
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState('general')

  const { data: settings, isLoading } = useQuery({
    queryKey: ['site-settings'],
    queryFn: siteSettingsApi.get,
  })

  const [formData, setFormData] = useState(null)

  // Initialize form data when settings load
  useState(() => {
    if (settings && !formData) {
      setFormData(settings)
    }
  }, [settings])

  const updateMutation = useMutation({
    mutationFn: siteSettingsApi.update,
    onSuccess: () => {
      queryClient.invalidateQueries(['site-settings'])
      toast({
        title: 'Settings saved',
        description: 'Your site settings have been updated successfully.',
        variant: 'success',
      })
    },
    onError: () => {
      toast({
        title: 'Error saving settings',
        description: 'Failed to save settings. Please try again.',
        variant: 'error',
      })
    },
  })

  const handleSave = () => {
    updateMutation.mutate(formData || settings)
  }

  const updateField = (section, field, value) => {
    setFormData((prev) => ({
      ...(prev || settings),
      [section]: {
        ...(prev || settings)?.[section],
        [field]: value,
      },
    }))
  }

  const currentData = formData || settings

  if (isLoading || !currentData) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  const tabs = [
    { id: 'general', label: 'General', icon: Globe },
    { id: 'branding', label: 'Branding', icon: Image },
    { id: 'social', label: 'Social Media', icon: Link },
    { id: 'advanced', label: 'Advanced', icon: AlertCircle },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Site Settings</h1>
          <p className="text-gray-600 mt-1">Configure your website's global settings</p>
        </div>
        <button
          onClick={handleSave}
          disabled={updateMutation.isPending}
          className="btn btn-primary"
        >
          <Save className="h-4 w-4 mr-2" />
          {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
        </button>
      </div>

      <div className="flex gap-6">
        {/* Tabs */}
        <div className="w-48 flex-shrink-0">
          <nav className="space-y-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                <tab.icon className="h-5 w-5" />
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1 bg-white rounded-xl shadow-sm border border-gray-200">
          {activeTab === 'general' && (
            <div className="p-6 space-y-6">
              <div>
                <h2 className="text-lg font-semibold text-gray-900 mb-4">General Settings</h2>

                <div className="grid gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Site Name
                    </label>
                    <input
                      type="text"
                      value={currentData.general.siteName}
                      onChange={(e) => updateField('general', 'siteName', e.target.value)}
                      className="input"
                      placeholder="My Website"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Tagline
                    </label>
                    <input
                      type="text"
                      value={currentData.general.tagline}
                      onChange={(e) => updateField('general', 'tagline', e.target.value)}
                      className="input"
                      placeholder="A short description of your site"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      <Link className="h-4 w-4 inline mr-1" />
                      Site URL
                    </label>
                    <input
                      type="url"
                      value={currentData.general.siteUrl}
                      onChange={(e) => updateField('general', 'siteUrl', e.target.value)}
                      className="input"
                      placeholder="https://example.com"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      <Mail className="h-4 w-4 inline mr-1" />
                      Admin Email
                    </label>
                    <input
                      type="email"
                      value={currentData.general.adminEmail}
                      onChange={(e) => updateField('general', 'adminEmail', e.target.value)}
                      className="input"
                      placeholder="admin@example.com"
                    />
                    <p className="text-sm text-gray-500 mt-1">
                      Used for admin notifications and contact form submissions
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        <MapPin className="h-4 w-4 inline mr-1" />
                        Timezone
                      </label>
                      <select
                        value={currentData.general.timezone}
                        onChange={(e) => updateField('general', 'timezone', e.target.value)}
                        className="input"
                      >
                        {timezones.map((tz) => (
                          <option key={tz} value={tz}>{tz}</option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        <Clock className="h-4 w-4 inline mr-1" />
                        Time Format
                      </label>
                      <select
                        value={currentData.general.timeFormat}
                        onChange={(e) => updateField('general', 'timeFormat', e.target.value)}
                        className="input"
                      >
                        {timeFormats.map((format) => (
                          <option key={format.value} value={format.value}>{format.label}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Date Format
                    </label>
                    <select
                      value={currentData.general.dateFormat}
                      onChange={(e) => updateField('general', 'dateFormat', e.target.value)}
                      className="input"
                    >
                      {dateFormats.map((format) => (
                        <option key={format.value} value={format.value}>{format.label}</option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'branding' && (
            <div className="p-6 space-y-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Branding</h2>

              <div className="grid gap-6">
                {/* Logo Upload */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Site Logo
                  </label>
                  <div className="flex items-start gap-4">
                    <div className="w-32 h-32 bg-gray-100 rounded-lg border-2 border-dashed border-gray-300 flex items-center justify-center">
                      {currentData.branding.logo ? (
                        <img
                          src={currentData.branding.logo}
                          alt="Logo"
                          className="max-w-full max-h-full object-contain"
                        />
                      ) : (
                        <Image className="h-8 w-8 text-gray-400" />
                      )}
                    </div>
                    <div className="space-y-2">
                      <button className="btn btn-secondary">
                        <Upload className="h-4 w-4 mr-2" />
                        Upload Logo
                      </button>
                      {currentData.branding.logo && (
                        <button
                          onClick={() => updateField('branding', 'logo', null)}
                          className="btn btn-secondary text-red-600"
                        >
                          <Trash2 className="h-4 w-4 mr-2" />
                          Remove
                        </button>
                      )}
                      <p className="text-sm text-gray-500">
                        Recommended: 200x50px, PNG or SVG
                      </p>
                    </div>
                  </div>
                </div>

                {/* Favicon Upload */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Favicon
                  </label>
                  <div className="flex items-start gap-4">
                    <div className="w-16 h-16 bg-gray-100 rounded-lg border-2 border-dashed border-gray-300 flex items-center justify-center">
                      {currentData.branding.favicon ? (
                        <img
                          src={currentData.branding.favicon}
                          alt="Favicon"
                          className="max-w-full max-h-full object-contain"
                        />
                      ) : (
                        <Globe className="h-6 w-6 text-gray-400" />
                      )}
                    </div>
                    <div className="space-y-2">
                      <button className="btn btn-secondary">
                        <Upload className="h-4 w-4 mr-2" />
                        Upload Favicon
                      </button>
                      <p className="text-sm text-gray-500">
                        Recommended: 32x32px or 64x64px, ICO or PNG
                      </p>
                    </div>
                  </div>
                </div>

                {/* Colors */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Primary Color
                    </label>
                    <div className="flex items-center gap-3">
                      <input
                        type="color"
                        value={currentData.branding.primaryColor}
                        onChange={(e) => updateField('branding', 'primaryColor', e.target.value)}
                        className="w-12 h-10 rounded border border-gray-300 cursor-pointer"
                      />
                      <input
                        type="text"
                        value={currentData.branding.primaryColor}
                        onChange={(e) => updateField('branding', 'primaryColor', e.target.value)}
                        className="input flex-1 font-mono"
                        placeholder="#3b82f6"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Secondary Color
                    </label>
                    <div className="flex items-center gap-3">
                      <input
                        type="color"
                        value={currentData.branding.secondaryColor}
                        onChange={(e) => updateField('branding', 'secondaryColor', e.target.value)}
                        className="w-12 h-10 rounded border border-gray-300 cursor-pointer"
                      />
                      <input
                        type="text"
                        value={currentData.branding.secondaryColor}
                        onChange={(e) => updateField('branding', 'secondaryColor', e.target.value)}
                        className="input flex-1 font-mono"
                        placeholder="#64748b"
                      />
                    </div>
                  </div>
                </div>

                {/* Preview */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    <Eye className="h-4 w-4 inline mr-1" />
                    Preview
                  </label>
                  <div className="border border-gray-200 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-4">
                      <div
                        className="w-8 h-8 rounded"
                        style={{ backgroundColor: currentData.branding.primaryColor }}
                      />
                      <span className="font-semibold">{currentData.general.siteName}</span>
                    </div>
                    <button
                      className="px-4 py-2 rounded text-white text-sm"
                      style={{ backgroundColor: currentData.branding.primaryColor }}
                    >
                      Primary Button
                    </button>
                    <button
                      className="ml-2 px-4 py-2 rounded text-white text-sm"
                      style={{ backgroundColor: currentData.branding.secondaryColor }}
                    >
                      Secondary Button
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'social' && (
            <div className="p-6 space-y-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Social Media Links</h2>
              <p className="text-gray-600 mb-6">
                Add your social media profiles. These will be displayed in the footer and shared across your site.
              </p>

              <div className="grid gap-4">
                {[
                  { key: 'facebook', label: 'Facebook', placeholder: 'https://facebook.com/yourpage' },
                  { key: 'twitter', label: 'Twitter / X', placeholder: 'https://twitter.com/yourhandle' },
                  { key: 'instagram', label: 'Instagram', placeholder: 'https://instagram.com/yourprofile' },
                  { key: 'linkedin', label: 'LinkedIn', placeholder: 'https://linkedin.com/company/yourcompany' },
                  { key: 'youtube', label: 'YouTube', placeholder: 'https://youtube.com/@yourchannel' },
                ].map((social) => (
                  <div key={social.key}>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      {social.label}
                    </label>
                    <input
                      type="url"
                      value={currentData.social[social.key] || ''}
                      onChange={(e) => updateField('social', social.key, e.target.value)}
                      className="input"
                      placeholder={social.placeholder}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'advanced' && (
            <div className="p-6 space-y-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Advanced Settings</h2>

              <div className="space-y-6">
                {/* Maintenance Mode */}
                <div className="bg-amber-50 rounded-lg p-4">
                  <div className="flex items-start gap-4">
                    <input
                      type="checkbox"
                      id="maintenanceMode"
                      checked={currentData.advanced.maintenanceMode}
                      onChange={(e) => updateField('advanced', 'maintenanceMode', e.target.checked)}
                      className="mt-1 h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    />
                    <div className="flex-1">
                      <label htmlFor="maintenanceMode" className="font-medium text-gray-900">
                        Maintenance Mode
                      </label>
                      <p className="text-sm text-gray-600 mt-1">
                        When enabled, visitors will see a maintenance message instead of your site content.
                      </p>
                      {currentData.advanced.maintenanceMode && (
                        <div className="mt-3">
                          <label className="block text-sm font-medium text-gray-700 mb-2">
                            Maintenance Message
                          </label>
                          <textarea
                            value={currentData.advanced.maintenanceMessage}
                            onChange={(e) => updateField('advanced', 'maintenanceMessage', e.target.value)}
                            className="input"
                            rows={3}
                          />
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Registration Settings */}
                <div className="space-y-4">
                  <h3 className="text-sm font-semibold text-gray-900">User Registration</h3>

                  <div className="flex items-center gap-4">
                    <input
                      type="checkbox"
                      id="allowRegistration"
                      checked={currentData.advanced.allowRegistration}
                      onChange={(e) => updateField('advanced', 'allowRegistration', e.target.checked)}
                      className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    />
                    <label htmlFor="allowRegistration" className="text-sm text-gray-700">
                      Allow new user registrations
                    </label>
                  </div>

                  <div className="flex items-center gap-4">
                    <input
                      type="checkbox"
                      id="requireEmailVerification"
                      checked={currentData.advanced.requireEmailVerification}
                      onChange={(e) => updateField('advanced', 'requireEmailVerification', e.target.checked)}
                      className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    />
                    <label htmlFor="requireEmailVerification" className="text-sm text-gray-700">
                      Require email verification for new accounts
                    </label>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Default Role for New Users
                    </label>
                    <select
                      value={currentData.advanced.defaultUserRole}
                      onChange={(e) => updateField('advanced', 'defaultUserRole', e.target.value)}
                      className="input max-w-xs"
                    >
                      <option value="subscriber">Subscriber</option>
                      <option value="contributor">Contributor</option>
                      <option value="author">Author</option>
                      <option value="editor">Editor</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default SiteSettingsPage
