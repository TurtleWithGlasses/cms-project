import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { privacyApi } from '../../services/api'
import { useToast } from '../../components/ui/Toast'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import {
  Shield,
  Cookie,
  FileText,
  Download,
  Trash2,
  Eye,
  Lock,
  Bell,
  Save,
  AlertTriangle,
  CheckCircle,
  Info,
} from 'lucide-react'

// Mock settings for demo
const mockPrivacySettings = {
  cookieConsent: {
    enabled: true,
    requireConsent: true,
    consentMessage: 'We use cookies to enhance your browsing experience.',
    cookieTypes: {
      essential: true,
      analytics: true,
      marketing: false,
      preferences: true,
    },
  },
  dataRetention: {
    userDataDays: 365,
    activityLogDays: 90,
    sessionDataDays: 30,
    deletedContentDays: 30,
  },
  privacyPolicy: {
    url: '/privacy-policy',
    lastUpdated: '2024-01-15',
    version: '2.1',
  },
  gdpr: {
    enabled: true,
    dataExportEnabled: true,
    dataDeleteEnabled: true,
    consentLogging: true,
  },
  anonymization: {
    anonymizeDeleted: true,
    anonymizeInactive: false,
    inactiveDays: 730,
  },
}

function PrivacySettingsPage() {
  const queryClient = useQueryClient()
  const toast = useToast()
  const [settings, setSettings] = useState(mockPrivacySettings)
  const [activeSection, setActiveSection] = useState('cookies')

  // Fetch settings
  const { isLoading } = useQuery({
    queryKey: ['privacy-settings'],
    queryFn: () => privacyApi.getSettings(),
    select: (res) => res.data || mockPrivacySettings,
    onSuccess: (data) => setSettings(data),
    placeholderData: mockPrivacySettings,
  })

  // Save mutation
  const saveMutation = useMutation({
    mutationFn: () => privacyApi.updateSettings(settings),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['privacy-settings'] })
      toast.success('Privacy settings saved successfully')
    },
    onError: () => toast.error('Failed to save settings'),
  })

  const handleChange = (section, field, value) => {
    setSettings((prev) => ({
      ...prev,
      [section]: {
        ...prev[section],
        [field]: value,
      },
    }))
  }

  const handleNestedChange = (section, parent, field, value) => {
    setSettings((prev) => ({
      ...prev,
      [section]: {
        ...prev[section],
        [parent]: {
          ...prev[section][parent],
          [field]: value,
        },
      },
    }))
  }

  const sections = [
    { id: 'cookies', name: 'Cookie Consent', icon: Cookie },
    { id: 'gdpr', name: 'GDPR Compliance', icon: Shield },
    { id: 'retention', name: 'Data Retention', icon: FileText },
    { id: 'anonymization', name: 'Data Anonymization', icon: Lock },
  ]

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Privacy Settings</h1>
          <p className="text-gray-500 mt-1">Manage GDPR compliance and data privacy</p>
        </div>
        <Button onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
          <Save className="h-4 w-4 mr-2" />
          Save Changes
        </Button>
      </div>

      {/* GDPR Status Banner */}
      <Card className={settings.gdpr.enabled ? 'border-green-200 bg-green-50' : 'border-yellow-200 bg-yellow-50'}>
        <CardContent className="p-4">
          <div className="flex items-center gap-3">
            {settings.gdpr.enabled ? (
              <CheckCircle className="h-6 w-6 text-green-600" />
            ) : (
              <AlertTriangle className="h-6 w-6 text-yellow-600" />
            )}
            <div>
              <p className={`font-medium ${settings.gdpr.enabled ? 'text-green-800' : 'text-yellow-800'}`}>
                {settings.gdpr.enabled ? 'GDPR Compliance Enabled' : 'GDPR Compliance Disabled'}
              </p>
              <p className={`text-sm ${settings.gdpr.enabled ? 'text-green-600' : 'text-yellow-600'}`}>
                {settings.gdpr.enabled
                  ? 'Your site is configured for GDPR compliance'
                  : 'Enable GDPR features to ensure compliance with data protection regulations'}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Sidebar navigation */}
        <Card className="lg:col-span-1">
          <CardContent className="p-2">
            <nav className="space-y-1">
              {sections.map((section) => (
                <button
                  key={section.id}
                  onClick={() => setActiveSection(section.id)}
                  className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    activeSection === section.id
                      ? 'bg-primary-100 text-primary-700'
                      : 'text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  <section.icon className="h-5 w-5" />
                  {section.name}
                </button>
              ))}
            </nav>
          </CardContent>
        </Card>

        {/* Settings content */}
        <div className="lg:col-span-3">
          {activeSection === 'cookies' && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Cookie className="h-5 w-5" />
                  Cookie Consent Settings
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex items-center justify-between py-3 border-b border-gray-200">
                  <div>
                    <p className="font-medium text-gray-900">Enable Cookie Banner</p>
                    <p className="text-sm text-gray-500">Show cookie consent popup to visitors</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.cookieConsent.enabled}
                      onChange={(e) => handleChange('cookieConsent', 'enabled', e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                  </label>
                </div>

                <div className="flex items-center justify-between py-3 border-b border-gray-200">
                  <div>
                    <p className="font-medium text-gray-900">Require Explicit Consent</p>
                    <p className="text-sm text-gray-500">Block non-essential cookies until user consents</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.cookieConsent.requireConsent}
                      onChange={(e) => handleChange('cookieConsent', 'requireConsent', e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                  </label>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Consent Message
                  </label>
                  <textarea
                    rows={3}
                    value={settings.cookieConsent.consentMessage}
                    onChange={(e) => handleChange('cookieConsent', 'consentMessage', e.target.value)}
                    className="input"
                  />
                </div>

                <div>
                  <h4 className="font-medium text-gray-900 mb-3">Cookie Categories</h4>
                  <div className="space-y-3">
                    {Object.entries(settings.cookieConsent.cookieTypes).map(([type, enabled]) => (
                      <label
                        key={type}
                        className="flex items-center justify-between p-3 rounded-lg border border-gray-200 cursor-pointer hover:bg-gray-50"
                      >
                        <div>
                          <p className="font-medium text-gray-900 capitalize">{type}</p>
                          <p className="text-sm text-gray-500">
                            {type === 'essential' && 'Required for basic site functionality'}
                            {type === 'analytics' && 'Help us understand how visitors use our site'}
                            {type === 'marketing' && 'Used for targeted advertising'}
                            {type === 'preferences' && 'Remember user preferences and settings'}
                          </p>
                        </div>
                        <input
                          type="checkbox"
                          checked={enabled}
                          disabled={type === 'essential'}
                          onChange={(e) =>
                            handleNestedChange('cookieConsent', 'cookieTypes', type, e.target.checked)
                          }
                          className="h-4 w-4 text-primary-600 rounded border-gray-300 focus:ring-primary-500"
                        />
                      </label>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {activeSection === 'gdpr' && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="h-5 w-5" />
                  GDPR Compliance
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex items-center justify-between py-3 border-b border-gray-200">
                  <div>
                    <p className="font-medium text-gray-900">Enable GDPR Features</p>
                    <p className="text-sm text-gray-500">Activate all GDPR compliance features</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.gdpr.enabled}
                      onChange={(e) => handleChange('gdpr', 'enabled', e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                  </label>
                </div>

                <div className="flex items-center justify-between py-3 border-b border-gray-200">
                  <div className="flex items-center gap-3">
                    <Download className="h-5 w-5 text-gray-400" />
                    <div>
                      <p className="font-medium text-gray-900">Data Export (Right to Portability)</p>
                      <p className="text-sm text-gray-500">Allow users to download their personal data</p>
                    </div>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.gdpr.dataExportEnabled}
                      onChange={(e) => handleChange('gdpr', 'dataExportEnabled', e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                  </label>
                </div>

                <div className="flex items-center justify-between py-3 border-b border-gray-200">
                  <div className="flex items-center gap-3">
                    <Trash2 className="h-5 w-5 text-gray-400" />
                    <div>
                      <p className="font-medium text-gray-900">Data Deletion (Right to Erasure)</p>
                      <p className="text-sm text-gray-500">Allow users to request deletion of their data</p>
                    </div>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.gdpr.dataDeleteEnabled}
                      onChange={(e) => handleChange('gdpr', 'dataDeleteEnabled', e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                  </label>
                </div>

                <div className="flex items-center justify-between py-3">
                  <div className="flex items-center gap-3">
                    <FileText className="h-5 w-5 text-gray-400" />
                    <div>
                      <p className="font-medium text-gray-900">Consent Logging</p>
                      <p className="text-sm text-gray-500">Keep records of user consent for auditing</p>
                    </div>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.gdpr.consentLogging}
                      onChange={(e) => handleChange('gdpr', 'consentLogging', e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                  </label>
                </div>

                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <Info className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="font-medium text-blue-800">Privacy Policy</p>
                      <p className="text-sm text-blue-600 mt-1">
                        Last updated: {settings.privacyPolicy.lastUpdated} (Version {settings.privacyPolicy.version})
                      </p>
                      <a
                        href={settings.privacyPolicy.url}
                        className="text-sm text-blue-700 hover:underline mt-2 inline-block"
                      >
                        View Privacy Policy
                      </a>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {activeSection === 'retention' && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="h-5 w-5" />
                  Data Retention Policies
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <p className="text-sm text-gray-500">
                  Configure how long different types of data are retained before automatic deletion.
                </p>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Input
                    label="User Data Retention (days)"
                    type="number"
                    value={settings.dataRetention.userDataDays}
                    onChange={(e) => handleChange('dataRetention', 'userDataDays', parseInt(e.target.value))}
                    min={30}
                  />
                  <Input
                    label="Activity Logs Retention (days)"
                    type="number"
                    value={settings.dataRetention.activityLogDays}
                    onChange={(e) => handleChange('dataRetention', 'activityLogDays', parseInt(e.target.value))}
                    min={7}
                  />
                  <Input
                    label="Session Data Retention (days)"
                    type="number"
                    value={settings.dataRetention.sessionDataDays}
                    onChange={(e) => handleChange('dataRetention', 'sessionDataDays', parseInt(e.target.value))}
                    min={1}
                  />
                  <Input
                    label="Deleted Content Retention (days)"
                    type="number"
                    value={settings.dataRetention.deletedContentDays}
                    onChange={(e) => handleChange('dataRetention', 'deletedContentDays', parseInt(e.target.value))}
                    min={0}
                  />
                </div>

                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <AlertTriangle className="h-5 w-5 text-yellow-600 flex-shrink-0 mt-0.5" />
                    <p className="text-sm text-yellow-700">
                      Data older than the retention period will be automatically deleted.
                      Make sure to backup important data before reducing retention periods.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {activeSection === 'anonymization' && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Lock className="h-5 w-5" />
                  Data Anonymization
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex items-center justify-between py-3 border-b border-gray-200">
                  <div>
                    <p className="font-medium text-gray-900">Anonymize Deleted Users</p>
                    <p className="text-sm text-gray-500">Replace personal data with anonymous placeholders</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.anonymization.anonymizeDeleted}
                      onChange={(e) => handleChange('anonymization', 'anonymizeDeleted', e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                  </label>
                </div>

                <div className="flex items-center justify-between py-3 border-b border-gray-200">
                  <div>
                    <p className="font-medium text-gray-900">Anonymize Inactive Users</p>
                    <p className="text-sm text-gray-500">Automatically anonymize users after inactivity period</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.anonymization.anonymizeInactive}
                      onChange={(e) => handleChange('anonymization', 'anonymizeInactive', e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                  </label>
                </div>

                {settings.anonymization.anonymizeInactive && (
                  <Input
                    label="Inactivity Period (days)"
                    type="number"
                    value={settings.anonymization.inactiveDays}
                    onChange={(e) => handleChange('anonymization', 'inactiveDays', parseInt(e.target.value))}
                    min={365}
                  />
                )}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}

export default PrivacySettingsPage
