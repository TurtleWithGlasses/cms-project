import { useState, useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
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
  RefreshCw,
} from 'lucide-react'
import { useToast } from '../../components/ui/Toast'

// Validation schemas for each section
const generalSchema = z.object({
  siteName: z.string()
    .min(1, 'Site name is required')
    .min(2, 'Site name must be at least 2 characters')
    .max(100, 'Site name must be less than 100 characters'),
  tagline: z.string()
    .max(200, 'Tagline must be less than 200 characters')
    .optional()
    .or(z.literal('')),
  siteUrl: z.string()
    .min(1, 'Site URL is required')
    .url('Please enter a valid URL'),
  adminEmail: z.string()
    .min(1, 'Admin email is required')
    .email('Please enter a valid email address'),
  timezone: z.string().min(1, 'Timezone is required'),
  dateFormat: z.string().min(1, 'Date format is required'),
  timeFormat: z.string().min(1, 'Time format is required'),
})

const brandingSchema = z.object({
  logo: z.string().nullable().optional(),
  favicon: z.string().nullable().optional(),
  primaryColor: z.string()
    .regex(/^#[0-9A-Fa-f]{6}$/, 'Please enter a valid hex color (e.g., #3b82f6)'),
  secondaryColor: z.string()
    .regex(/^#[0-9A-Fa-f]{6}$/, 'Please enter a valid hex color (e.g., #64748b)'),
})

const socialSchema = z.object({
  facebook: z.string()
    .url('Please enter a valid URL')
    .optional()
    .or(z.literal('')),
  twitter: z.string()
    .url('Please enter a valid URL')
    .optional()
    .or(z.literal('')),
  instagram: z.string()
    .url('Please enter a valid URL')
    .optional()
    .or(z.literal('')),
  linkedin: z.string()
    .url('Please enter a valid URL')
    .optional()
    .or(z.literal('')),
  youtube: z.string()
    .url('Please enter a valid URL')
    .optional()
    .or(z.literal('')),
})

const advancedSchema = z.object({
  maintenanceMode: z.boolean(),
  maintenanceMessage: z.string()
    .max(500, 'Maintenance message must be less than 500 characters')
    .optional()
    .or(z.literal('')),
  allowRegistration: z.boolean(),
  requireEmailVerification: z.boolean(),
  defaultUserRole: z.enum(['subscriber', 'contributor', 'author', 'editor']),
})

// Combined schema for all settings
const settingsSchema = z.object({
  general: generalSchema,
  branding: brandingSchema,
  social: socialSchema,
  advanced: advancedSchema,
})

// Mock Site Settings API (replace with real API when backend endpoint is available)
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

  const { data: settings, isLoading, error, refetch } = useQuery({
    queryKey: ['site-settings'],
    queryFn: siteSettingsApi.get,
  })

  const {
    register,
    handleSubmit,
    formState: { errors, isDirty },
    reset,
    watch,
    setValue,
  } = useForm({
    resolver: zodResolver(settingsSchema),
    defaultValues: {
      general: {
        siteName: '',
        tagline: '',
        siteUrl: '',
        adminEmail: '',
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
        maintenanceMessage: '',
        allowRegistration: true,
        requireEmailVerification: true,
        defaultUserRole: 'subscriber',
      },
    },
  })

  // Watch for preview
  const watchedValues = watch()
  const maintenanceMode = watch('advanced.maintenanceMode')

  // Reset form when settings load
  useEffect(() => {
    if (settings) {
      reset(settings)
    }
  }, [settings, reset])

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
    onError: (error) => {
      toast({
        title: 'Error saving settings',
        description: error.message || 'Failed to save settings. Please try again.',
        variant: 'error',
      })
    },
  })

  const onSubmit = (data) => {
    updateMutation.mutate(data)
  }

  // Check if current tab has errors
  const hasTabErrors = (tabId) => {
    return errors[tabId] && Object.keys(errors[tabId]).length > 0
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 space-y-4">
        <AlertCircle className="h-12 w-12 text-red-500" />
        <p className="text-gray-600 dark:text-gray-400">Failed to load site settings</p>
        <button
          onClick={() => refetch()}
          className="btn btn-secondary flex items-center gap-2"
        >
          <RefreshCw className="h-4 w-4" />
          Retry
        </button>
      </div>
    )
  }

  if (isLoading || !settings) {
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
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Site Settings</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">Configure your website's global settings</p>
        </div>
        <button
          type="submit"
          disabled={updateMutation.isPending || !isDirty}
          className="btn btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
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
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/50 dark:text-primary-300'
                    : 'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800'
                }`}
              >
                <tab.icon className="h-5 w-5" />
                {tab.label}
                {hasTabErrors(tab.id) && (
                  <span className="ml-auto h-2 w-2 rounded-full bg-red-500" />
                )}
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1 bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
          {activeTab === 'general' && (
            <div className="p-6 space-y-6">
              <div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">General Settings</h2>

                <div className="grid gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Site Name *
                    </label>
                    <input
                      type="text"
                      {...register('general.siteName')}
                      className={`input dark:bg-gray-700 dark:border-gray-600 dark:text-white ${
                        errors.general?.siteName ? 'border-red-500 focus:ring-red-500' : ''
                      }`}
                      placeholder="My Website"
                    />
                    {errors.general?.siteName && (
                      <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                        {errors.general.siteName.message}
                      </p>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Tagline
                    </label>
                    <input
                      type="text"
                      {...register('general.tagline')}
                      className={`input dark:bg-gray-700 dark:border-gray-600 dark:text-white ${
                        errors.general?.tagline ? 'border-red-500 focus:ring-red-500' : ''
                      }`}
                      placeholder="A short description of your site"
                    />
                    {errors.general?.tagline && (
                      <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                        {errors.general.tagline.message}
                      </p>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      <Link className="h-4 w-4 inline mr-1" />
                      Site URL *
                    </label>
                    <input
                      type="url"
                      {...register('general.siteUrl')}
                      className={`input dark:bg-gray-700 dark:border-gray-600 dark:text-white ${
                        errors.general?.siteUrl ? 'border-red-500 focus:ring-red-500' : ''
                      }`}
                      placeholder="https://example.com"
                    />
                    {errors.general?.siteUrl && (
                      <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                        {errors.general.siteUrl.message}
                      </p>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      <Mail className="h-4 w-4 inline mr-1" />
                      Admin Email *
                    </label>
                    <input
                      type="email"
                      {...register('general.adminEmail')}
                      className={`input dark:bg-gray-700 dark:border-gray-600 dark:text-white ${
                        errors.general?.adminEmail ? 'border-red-500 focus:ring-red-500' : ''
                      }`}
                      placeholder="admin@example.com"
                    />
                    {errors.general?.adminEmail && (
                      <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                        {errors.general.adminEmail.message}
                      </p>
                    )}
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                      Used for admin notifications and contact form submissions
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        <MapPin className="h-4 w-4 inline mr-1" />
                        Timezone
                      </label>
                      <select
                        {...register('general.timezone')}
                        className="input dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                      >
                        {timezones.map((tz) => (
                          <option key={tz} value={tz}>{tz}</option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        <Clock className="h-4 w-4 inline mr-1" />
                        Time Format
                      </label>
                      <select
                        {...register('general.timeFormat')}
                        className="input dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                      >
                        {timeFormats.map((format) => (
                          <option key={format.value} value={format.value}>{format.label}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Date Format
                    </label>
                    <select
                      {...register('general.dateFormat')}
                      className="input dark:bg-gray-700 dark:border-gray-600 dark:text-white"
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
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Branding</h2>

              <div className="grid gap-6">
                {/* Logo Upload */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Site Logo
                  </label>
                  <div className="flex items-start gap-4">
                    <div className="w-32 h-32 bg-gray-100 dark:bg-gray-700 rounded-lg border-2 border-dashed border-gray-300 dark:border-gray-600 flex items-center justify-center">
                      {watchedValues.branding?.logo ? (
                        <img
                          src={watchedValues.branding.logo}
                          alt="Logo"
                          className="max-w-full max-h-full object-contain"
                        />
                      ) : (
                        <Image className="h-8 w-8 text-gray-400" />
                      )}
                    </div>
                    <div className="space-y-2">
                      <button type="button" className="btn btn-secondary">
                        <Upload className="h-4 w-4 mr-2" />
                        Upload Logo
                      </button>
                      {watchedValues.branding?.logo && (
                        <button
                          type="button"
                          onClick={() => setValue('branding.logo', null, { shouldDirty: true })}
                          className="btn btn-secondary text-red-600 dark:text-red-400"
                        >
                          <Trash2 className="h-4 w-4 mr-2" />
                          Remove
                        </button>
                      )}
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        Recommended: 200x50px, PNG or SVG
                      </p>
                    </div>
                  </div>
                </div>

                {/* Favicon Upload */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Favicon
                  </label>
                  <div className="flex items-start gap-4">
                    <div className="w-16 h-16 bg-gray-100 dark:bg-gray-700 rounded-lg border-2 border-dashed border-gray-300 dark:border-gray-600 flex items-center justify-center">
                      {watchedValues.branding?.favicon ? (
                        <img
                          src={watchedValues.branding.favicon}
                          alt="Favicon"
                          className="max-w-full max-h-full object-contain"
                        />
                      ) : (
                        <Globe className="h-6 w-6 text-gray-400" />
                      )}
                    </div>
                    <div className="space-y-2">
                      <button type="button" className="btn btn-secondary">
                        <Upload className="h-4 w-4 mr-2" />
                        Upload Favicon
                      </button>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        Recommended: 32x32px or 64x64px, ICO or PNG
                      </p>
                    </div>
                  </div>
                </div>

                {/* Colors */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Primary Color
                    </label>
                    <div className="flex items-center gap-3">
                      <input
                        type="color"
                        value={watchedValues.branding?.primaryColor || '#3b82f6'}
                        onChange={(e) => setValue('branding.primaryColor', e.target.value, { shouldDirty: true })}
                        className="w-12 h-10 rounded border border-gray-300 dark:border-gray-600 cursor-pointer"
                      />
                      <input
                        type="text"
                        {...register('branding.primaryColor')}
                        className={`input flex-1 font-mono dark:bg-gray-700 dark:border-gray-600 dark:text-white ${
                          errors.branding?.primaryColor ? 'border-red-500 focus:ring-red-500' : ''
                        }`}
                        placeholder="#3b82f6"
                      />
                    </div>
                    {errors.branding?.primaryColor && (
                      <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                        {errors.branding.primaryColor.message}
                      </p>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Secondary Color
                    </label>
                    <div className="flex items-center gap-3">
                      <input
                        type="color"
                        value={watchedValues.branding?.secondaryColor || '#64748b'}
                        onChange={(e) => setValue('branding.secondaryColor', e.target.value, { shouldDirty: true })}
                        className="w-12 h-10 rounded border border-gray-300 dark:border-gray-600 cursor-pointer"
                      />
                      <input
                        type="text"
                        {...register('branding.secondaryColor')}
                        className={`input flex-1 font-mono dark:bg-gray-700 dark:border-gray-600 dark:text-white ${
                          errors.branding?.secondaryColor ? 'border-red-500 focus:ring-red-500' : ''
                        }`}
                        placeholder="#64748b"
                      />
                    </div>
                    {errors.branding?.secondaryColor && (
                      <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                        {errors.branding.secondaryColor.message}
                      </p>
                    )}
                  </div>
                </div>

                {/* Preview */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    <Eye className="h-4 w-4 inline mr-1" />
                    Preview
                  </label>
                  <div className="border border-gray-200 dark:border-gray-600 rounded-lg p-4 bg-white dark:bg-gray-900">
                    <div className="flex items-center gap-2 mb-4">
                      <div
                        className="w-8 h-8 rounded"
                        style={{ backgroundColor: watchedValues.branding?.primaryColor || '#3b82f6' }}
                      />
                      <span className="font-semibold text-gray-900 dark:text-white">
                        {watchedValues.general?.siteName || 'Site Name'}
                      </span>
                    </div>
                    <button
                      type="button"
                      className="px-4 py-2 rounded text-white text-sm"
                      style={{ backgroundColor: watchedValues.branding?.primaryColor || '#3b82f6' }}
                    >
                      Primary Button
                    </button>
                    <button
                      type="button"
                      className="ml-2 px-4 py-2 rounded text-white text-sm"
                      style={{ backgroundColor: watchedValues.branding?.secondaryColor || '#64748b' }}
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
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Social Media Links</h2>
              <p className="text-gray-600 dark:text-gray-400 mb-6">
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
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      {social.label}
                    </label>
                    <input
                      type="url"
                      {...register(`social.${social.key}`)}
                      className={`input dark:bg-gray-700 dark:border-gray-600 dark:text-white ${
                        errors.social?.[social.key] ? 'border-red-500 focus:ring-red-500' : ''
                      }`}
                      placeholder={social.placeholder}
                    />
                    {errors.social?.[social.key] && (
                      <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                        {errors.social[social.key].message}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'advanced' && (
            <div className="p-6 space-y-6">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Advanced Settings</h2>

              <div className="space-y-6">
                {/* Maintenance Mode */}
                <div className="bg-amber-50 dark:bg-amber-900/20 rounded-lg p-4">
                  <div className="flex items-start gap-4">
                    <input
                      type="checkbox"
                      id="maintenanceMode"
                      {...register('advanced.maintenanceMode')}
                      className="mt-1 h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    />
                    <div className="flex-1">
                      <label htmlFor="maintenanceMode" className="font-medium text-gray-900 dark:text-white">
                        Maintenance Mode
                      </label>
                      <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                        When enabled, visitors will see a maintenance message instead of your site content.
                      </p>
                      {maintenanceMode && (
                        <div className="mt-3">
                          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Maintenance Message
                          </label>
                          <textarea
                            {...register('advanced.maintenanceMessage')}
                            className={`input dark:bg-gray-700 dark:border-gray-600 dark:text-white ${
                              errors.advanced?.maintenanceMessage ? 'border-red-500 focus:ring-red-500' : ''
                            }`}
                            rows={3}
                          />
                          {errors.advanced?.maintenanceMessage && (
                            <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                              {errors.advanced.maintenanceMessage.message}
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Registration Settings */}
                <div className="space-y-4">
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white">User Registration</h3>

                  <div className="flex items-center gap-4">
                    <input
                      type="checkbox"
                      id="allowRegistration"
                      {...register('advanced.allowRegistration')}
                      className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    />
                    <label htmlFor="allowRegistration" className="text-sm text-gray-700 dark:text-gray-300">
                      Allow new user registrations
                    </label>
                  </div>

                  <div className="flex items-center gap-4">
                    <input
                      type="checkbox"
                      id="requireEmailVerification"
                      {...register('advanced.requireEmailVerification')}
                      className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    />
                    <label htmlFor="requireEmailVerification" className="text-sm text-gray-700 dark:text-gray-300">
                      Require email verification for new accounts
                    </label>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Default Role for New Users
                    </label>
                    <select
                      {...register('advanced.defaultUserRole')}
                      className="input max-w-xs dark:bg-gray-700 dark:border-gray-600 dark:text-white"
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
    </form>
  )
}

export default SiteSettingsPage
