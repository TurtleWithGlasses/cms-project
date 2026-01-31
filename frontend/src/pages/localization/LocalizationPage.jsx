import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Globe,
  Plus,
  Save,
  Trash2,
  Check,
  X,
  ChevronDown,
  ChevronRight,
  Languages,
  Flag,
  Edit2,
  Copy,
  Search,
  AlertCircle,
} from 'lucide-react'
import { useToast } from '../../components/ui/Toast'
import { localizationApi } from '../../services/api'

// Available languages list (static reference data)
const availableLanguagesList = [
  { code: 'en', name: 'English', nativeName: 'English' },
  { code: 'es', name: 'Spanish', nativeName: 'Español' },
  { code: 'fr', name: 'French', nativeName: 'Français' },
  { code: 'de', name: 'German', nativeName: 'Deutsch' },
  { code: 'it', name: 'Italian', nativeName: 'Italiano' },
  { code: 'pt', name: 'Portuguese', nativeName: 'Português' },
  { code: 'zh', name: 'Chinese', nativeName: '中文' },
  { code: 'ja', name: 'Japanese', nativeName: '日本語' },
  { code: 'ko', name: 'Korean', nativeName: '한국어' },
  { code: 'ar', name: 'Arabic', nativeName: 'العربية' },
  { code: 'ru', name: 'Russian', nativeName: 'Русский' },
  { code: 'hi', name: 'Hindi', nativeName: 'हिन्दी' },
]

function LocalizationPage() {
  const [showAddLanguage, setShowAddLanguage] = useState(false)
  const [selectedLanguage, setSelectedLanguage] = useState(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [expandedGroups, setExpandedGroups] = useState(['common', 'nav', 'auth', 'content'])
  const [editingKey, setEditingKey] = useState(null)
  const [editValue, setEditValue] = useState('')

  const { toast } = useToast()
  const queryClient = useQueryClient()

  const { data: languages, isLoading: loadingLanguages } = useQuery({
    queryKey: ['languages'],
    queryFn: () => localizationApi.getLanguages().then(res => res.data),
  })

  // Use static list for available languages (reference data)
  const availableLanguages = availableLanguagesList

  const { data: translations, isLoading: loadingTranslations } = useQuery({
    queryKey: ['translations', selectedLanguage],
    queryFn: () => localizationApi.getTranslations(selectedLanguage).then(res => res.data),
    enabled: !!selectedLanguage,
  })

  const addLanguageMutation = useMutation({
    mutationFn: (code) => localizationApi.addLanguage(code),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['languages'] })
      setShowAddLanguage(false)
      toast({ title: 'Language added successfully', variant: 'success' })
    },
    onError: () => {
      toast({ title: 'Failed to add language', variant: 'error' })
    },
  })

  const removeLanguageMutation = useMutation({
    mutationFn: (code) => localizationApi.removeLanguage(code),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['languages'] })
      toast({ title: 'Language removed', variant: 'success' })
    },
    onError: () => {
      toast({ title: 'Failed to remove language', variant: 'error' })
    },
  })

  const setDefaultMutation = useMutation({
    mutationFn: (code) => localizationApi.setDefault(code),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['languages'] })
      toast({ title: 'Default language updated', variant: 'success' })
    },
    onError: () => {
      toast({ title: 'Failed to set default language', variant: 'error' })
    },
  })

  const toggleEnabledMutation = useMutation({
    mutationFn: ({ code, enabled }) => localizationApi.toggleEnabled(code, enabled),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['languages'] })
    },
    onError: () => {
      toast({ title: 'Failed to update language', variant: 'error' })
    },
  })

  const updateTranslationMutation = useMutation({
    mutationFn: ({ key, value }) => localizationApi.updateTranslation(selectedLanguage, key, value),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['translations', selectedLanguage] })
      setEditingKey(null)
      toast({ title: 'Translation updated', variant: 'success' })
    },
    onError: () => {
      toast({ title: 'Failed to update translation', variant: 'error' })
    },
  })

  const toggleGroup = (group) => {
    setExpandedGroups((prev) =>
      prev.includes(group) ? prev.filter((g) => g !== group) : [...prev, group]
    )
  }

  const groupedTranslations = translations
    ? Object.entries(translations).reduce((acc, [key, value]) => {
        const [group] = key.split('.')
        if (!acc[group]) acc[group] = []
        acc[group].push({ key, value })
        return acc
      }, {})
    : {}

  const filteredGroups = Object.entries(groupedTranslations).filter(([group, items]) => {
    if (!searchTerm) return true
    return items.some(
      (item) =>
        item.key.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.value.toLowerCase().includes(searchTerm.toLowerCase())
    )
  })

  const unusedLanguages = availableLanguages?.filter(
    (lang) => !languages?.some((l) => l.code === lang.code)
  )

  if (loadingLanguages) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Localization</h1>
          <p className="text-gray-600 mt-1">Manage languages and translations for your site</p>
        </div>
        <button
          onClick={() => setShowAddLanguage(true)}
          className="btn btn-primary"
        >
          <Plus className="h-4 w-4 mr-2" />
          Add Language
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Languages List */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200">
            <div className="p-4 border-b border-gray-200">
              <h2 className="font-semibold text-gray-900">Languages</h2>
              <p className="text-sm text-gray-500 mt-1">
                {languages?.filter((l) => l.isEnabled).length} of {languages?.length} enabled
              </p>
            </div>

            <div className="divide-y divide-gray-100">
              {languages?.map((lang) => (
                <div
                  key={lang.code}
                  className={`p-4 hover:bg-gray-50 cursor-pointer transition-colors ${
                    selectedLanguage === lang.code ? 'bg-primary-50 border-l-4 border-primary-500' : ''
                  }`}
                  onClick={() => setSelectedLanguage(lang.code)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center text-sm font-medium">
                        {lang.code.toUpperCase()}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-gray-900">{lang.name}</span>
                          {lang.isDefault && (
                            <span className="text-xs bg-primary-100 text-primary-700 px-1.5 py-0.5 rounded">
                              Default
                            </span>
                          )}
                        </div>
                        <span className="text-sm text-gray-500">{lang.nativeName}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="text-right">
                        <div className="text-sm font-medium text-gray-900">{lang.progress}%</div>
                        <div className="w-16 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              lang.progress === 100
                                ? 'bg-green-500'
                                : lang.progress >= 70
                                ? 'bg-blue-500'
                                : 'bg-amber-500'
                            }`}
                            style={{ width: `${lang.progress}%` }}
                          />
                        </div>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          toggleEnabledMutation.mutate({ code: lang.code, enabled: !lang.isEnabled })
                        }}
                        className={`p-1 rounded ${
                          lang.isEnabled ? 'text-green-600' : 'text-gray-400'
                        }`}
                      >
                        {lang.isEnabled ? (
                          <Check className="h-4 w-4" />
                        ) : (
                          <X className="h-4 w-4" />
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Translations Editor */}
        <div className="lg:col-span-2">
          {selectedLanguage ? (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200">
              <div className="p-4 border-b border-gray-200">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="font-semibold text-gray-900">
                      {languages?.find((l) => l.code === selectedLanguage)?.name} Translations
                    </h2>
                    <p className="text-sm text-gray-500 mt-1">
                      {translations ? Object.keys(translations).length : 0} translation keys
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    {!languages?.find((l) => l.code === selectedLanguage)?.isDefault && (
                      <button
                        onClick={() => setDefaultMutation.mutate(selectedLanguage)}
                        className="btn btn-secondary text-sm"
                      >
                        Set as Default
                      </button>
                    )}
                    <button className="btn btn-secondary text-sm">
                      <Copy className="h-4 w-4 mr-1" />
                      Export
                    </button>
                  </div>
                </div>

                {/* Search */}
                <div className="mt-4 relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search translations..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="input pl-10"
                  />
                </div>
              </div>

              {loadingTranslations ? (
                <div className="flex items-center justify-center h-64">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
                </div>
              ) : (
                <div className="max-h-[600px] overflow-y-auto">
                  {filteredGroups.map(([group, items]) => (
                    <div key={group} className="border-b border-gray-100 last:border-0">
                      <button
                        onClick={() => toggleGroup(group)}
                        className="w-full flex items-center justify-between p-4 hover:bg-gray-50 text-left"
                      >
                        <div className="flex items-center gap-2">
                          {expandedGroups.includes(group) ? (
                            <ChevronDown className="h-4 w-4 text-gray-400" />
                          ) : (
                            <ChevronRight className="h-4 w-4 text-gray-400" />
                          )}
                          <span className="font-medium text-gray-900 capitalize">{group}</span>
                          <span className="text-sm text-gray-500">({items.length})</span>
                        </div>
                      </button>

                      {expandedGroups.includes(group) && (
                        <div className="pb-2">
                          {items
                            .filter(
                              (item) =>
                                !searchTerm ||
                                item.key.toLowerCase().includes(searchTerm.toLowerCase()) ||
                                item.value.toLowerCase().includes(searchTerm.toLowerCase())
                            )
                            .map((item) => (
                              <div
                                key={item.key}
                                className="px-4 py-2 hover:bg-gray-50 group"
                              >
                                <div className="flex items-start justify-between gap-4">
                                  <div className="flex-1 min-w-0">
                                    <code className="text-xs text-gray-500 font-mono">
                                      {item.key}
                                    </code>
                                    {editingKey === item.key ? (
                                      <div className="mt-1 flex items-center gap-2">
                                        <input
                                          type="text"
                                          value={editValue}
                                          onChange={(e) => setEditValue(e.target.value)}
                                          className="input text-sm py-1"
                                          autoFocus
                                        />
                                        <button
                                          onClick={() =>
                                            updateTranslationMutation.mutate({
                                              key: item.key,
                                              value: editValue,
                                            })
                                          }
                                          className="p-1 text-green-600 hover:bg-green-50 rounded"
                                        >
                                          <Check className="h-4 w-4" />
                                        </button>
                                        <button
                                          onClick={() => setEditingKey(null)}
                                          className="p-1 text-gray-400 hover:bg-gray-100 rounded"
                                        >
                                          <X className="h-4 w-4" />
                                        </button>
                                      </div>
                                    ) : (
                                      <p className="text-sm text-gray-900 mt-0.5">{item.value}</p>
                                    )}
                                  </div>
                                  {editingKey !== item.key && (
                                    <button
                                      onClick={() => {
                                        setEditingKey(item.key)
                                        setEditValue(item.value)
                                      }}
                                      className="p-1 text-gray-400 hover:text-gray-600 opacity-0 group-hover:opacity-100 transition-opacity"
                                    >
                                      <Edit2 className="h-4 w-4" />
                                    </button>
                                  )}
                                </div>
                              </div>
                            ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
              <Languages className="h-12 w-12 text-gray-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">Select a Language</h3>
              <p className="text-gray-500">
                Choose a language from the list to view and edit its translations
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Add Language Modal */}
      {showAddLanguage && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4">
            <div className="fixed inset-0 bg-black/50" onClick={() => setShowAddLanguage(false)} />
            <div className="relative bg-white rounded-xl shadow-xl max-w-md w-full p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Add Language</h3>

              <div className="space-y-2 max-h-80 overflow-y-auto">
                {unusedLanguages?.map((lang) => (
                  <button
                    key={lang.code}
                    onClick={() => addLanguageMutation.mutate(lang.code)}
                    className="w-full flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 text-left"
                  >
                    <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center text-sm font-medium">
                      {lang.code.toUpperCase()}
                    </div>
                    <div>
                      <div className="font-medium text-gray-900">{lang.name}</div>
                      <div className="text-sm text-gray-500">{lang.nativeName}</div>
                    </div>
                  </button>
                ))}
              </div>

              <button
                onClick={() => setShowAddLanguage(false)}
                className="mt-4 btn btn-secondary w-full"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default LocalizationPage
