import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card'
import Input from '../ui/Input'
import {
  Search,
  Globe,
  Eye,
  AlertCircle,
  CheckCircle,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'

const MAX_TITLE_LENGTH = 60
const MAX_DESCRIPTION_LENGTH = 160

function SEOPanel({ values, onChange, slug = '' }) {
  const [isExpanded, setIsExpanded] = useState(true)
  const [showPreview, setShowPreview] = useState(true)

  const {
    metaTitle = '',
    metaDescription = '',
    metaKeywords = '',
    canonicalUrl = '',
    ogTitle = '',
    ogDescription = '',
    ogImage = '',
    twitterCard = 'summary_large_image',
    noIndex = false,
    noFollow = false,
  } = values || {}

  const handleChange = (field, value) => {
    onChange?.({ ...values, [field]: value })
  }

  const titleLength = metaTitle.length
  const descriptionLength = metaDescription.length

  const getTitleStatus = () => {
    if (titleLength === 0) return { color: 'text-gray-400', message: 'Add a title' }
    if (titleLength < 30) return { color: 'text-yellow-500', message: 'Too short' }
    if (titleLength > MAX_TITLE_LENGTH) return { color: 'text-red-500', message: 'Too long' }
    return { color: 'text-green-500', message: 'Good length' }
  }

  const getDescriptionStatus = () => {
    if (descriptionLength === 0) return { color: 'text-gray-400', message: 'Add a description' }
    if (descriptionLength < 70) return { color: 'text-yellow-500', message: 'Too short' }
    if (descriptionLength > MAX_DESCRIPTION_LENGTH) return { color: 'text-red-500', message: 'Too long' }
    return { color: 'text-green-500', message: 'Good length' }
  }

  const titleStatus = getTitleStatus()
  const descriptionStatus = getDescriptionStatus()

  return (
    <Card>
      <CardHeader className="cursor-pointer" onClick={() => setIsExpanded(!isExpanded)}>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Search className="h-5 w-5" />
            SEO Settings
          </CardTitle>
          {isExpanded ? (
            <ChevronUp className="h-5 w-5 text-gray-400" />
          ) : (
            <ChevronDown className="h-5 w-5 text-gray-400" />
          )}
        </div>
      </CardHeader>

      {isExpanded && (
        <CardContent className="space-y-6">
          {/* Google Preview */}
          {showPreview && (
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-3">
                <Eye className="h-4 w-4 text-gray-500" />
                <span className="text-sm font-medium text-gray-700">Search Preview</span>
              </div>
              <div className="bg-white rounded border border-gray-200 p-4">
                <div className="text-sm text-green-700 truncate">
                  example.com{slug ? `/${slug}` : ''}
                </div>
                <h3 className="text-lg text-blue-700 hover:underline cursor-pointer truncate mt-1">
                  {metaTitle || 'Page Title'}
                </h3>
                <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                  {metaDescription || 'Add a meta description to see how this page will appear in search results...'}
                </p>
              </div>
            </div>
          )}

          {/* Meta Title */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="block text-sm font-medium text-gray-700">
                Meta Title
              </label>
              <span className={`text-xs ${titleStatus.color}`}>
                {titleLength}/{MAX_TITLE_LENGTH} - {titleStatus.message}
              </span>
            </div>
            <Input
              value={metaTitle}
              onChange={(e) => handleChange('metaTitle', e.target.value)}
              placeholder="Enter SEO title"
            />
            <div className="mt-1 h-1 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all ${
                  titleLength === 0 ? 'bg-gray-300' :
                  titleLength < 30 ? 'bg-yellow-500' :
                  titleLength > MAX_TITLE_LENGTH ? 'bg-red-500' : 'bg-green-500'
                }`}
                style={{ width: `${Math.min((titleLength / MAX_TITLE_LENGTH) * 100, 100)}%` }}
              />
            </div>
          </div>

          {/* Meta Description */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="block text-sm font-medium text-gray-700">
                Meta Description
              </label>
              <span className={`text-xs ${descriptionStatus.color}`}>
                {descriptionLength}/{MAX_DESCRIPTION_LENGTH} - {descriptionStatus.message}
              </span>
            </div>
            <textarea
              rows={3}
              value={metaDescription}
              onChange={(e) => handleChange('metaDescription', e.target.value)}
              placeholder="Enter SEO description"
              className="input"
            />
            <div className="mt-1 h-1 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all ${
                  descriptionLength === 0 ? 'bg-gray-300' :
                  descriptionLength < 70 ? 'bg-yellow-500' :
                  descriptionLength > MAX_DESCRIPTION_LENGTH ? 'bg-red-500' : 'bg-green-500'
                }`}
                style={{ width: `${Math.min((descriptionLength / MAX_DESCRIPTION_LENGTH) * 100, 100)}%` }}
              />
            </div>
          </div>

          {/* Meta Keywords */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Meta Keywords
            </label>
            <Input
              value={metaKeywords}
              onChange={(e) => handleChange('metaKeywords', e.target.value)}
              placeholder="keyword1, keyword2, keyword3"
            />
            <p className="mt-1 text-xs text-gray-500">
              Separate keywords with commas (less important for modern SEO)
            </p>
          </div>

          {/* Canonical URL */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Canonical URL
            </label>
            <div className="flex items-center gap-2">
              <Globe className="h-4 w-4 text-gray-400" />
              <Input
                value={canonicalUrl}
                onChange={(e) => handleChange('canonicalUrl', e.target.value)}
                placeholder="https://example.com/page"
                className="flex-1"
              />
            </div>
            <p className="mt-1 text-xs text-gray-500">
              Leave empty to use the default URL
            </p>
          </div>

          {/* Social Media Section */}
          <div className="border-t border-gray-200 pt-6">
            <h4 className="font-medium text-gray-900 mb-4">Social Media</h4>

            <div className="space-y-4">
              <Input
                label="OG Title (Facebook/LinkedIn)"
                value={ogTitle}
                onChange={(e) => handleChange('ogTitle', e.target.value)}
                placeholder="Social media title (defaults to meta title)"
              />

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  OG Description
                </label>
                <textarea
                  rows={2}
                  value={ogDescription}
                  onChange={(e) => handleChange('ogDescription', e.target.value)}
                  placeholder="Social media description (defaults to meta description)"
                  className="input"
                />
              </div>

              <Input
                label="OG Image URL"
                value={ogImage}
                onChange={(e) => handleChange('ogImage', e.target.value)}
                placeholder="https://example.com/image.jpg"
              />

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Twitter Card Type
                </label>
                <select
                  value={twitterCard}
                  onChange={(e) => handleChange('twitterCard', e.target.value)}
                  className="input"
                >
                  <option value="summary">Summary</option>
                  <option value="summary_large_image">Summary with Large Image</option>
                  <option value="app">App</option>
                  <option value="player">Player</option>
                </select>
              </div>
            </div>
          </div>

          {/* Advanced Section */}
          <div className="border-t border-gray-200 pt-6">
            <h4 className="font-medium text-gray-900 mb-4">Advanced</h4>

            <div className="space-y-3">
              <label className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 cursor-pointer">
                <input
                  type="checkbox"
                  checked={noIndex}
                  onChange={(e) => handleChange('noIndex', e.target.checked)}
                  className="h-4 w-4 text-primary-600 rounded border-gray-300 focus:ring-primary-500"
                />
                <div>
                  <p className="font-medium text-gray-900">No Index</p>
                  <p className="text-sm text-gray-500">Prevent search engines from indexing this page</p>
                </div>
              </label>

              <label className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 cursor-pointer">
                <input
                  type="checkbox"
                  checked={noFollow}
                  onChange={(e) => handleChange('noFollow', e.target.checked)}
                  className="h-4 w-4 text-primary-600 rounded border-gray-300 focus:ring-primary-500"
                />
                <div>
                  <p className="font-medium text-gray-900">No Follow</p>
                  <p className="text-sm text-gray-500">Prevent search engines from following links on this page</p>
                </div>
              </label>
            </div>

            {(noIndex || noFollow) && (
              <div className="mt-4 flex items-start gap-2 p-3 bg-yellow-50 rounded-lg">
                <AlertCircle className="h-5 w-5 text-yellow-600 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-yellow-700">
                  {noIndex && noFollow
                    ? 'This page will not be indexed and links will not be followed by search engines.'
                    : noIndex
                    ? 'This page will not appear in search engine results.'
                    : 'Links on this page will not be followed by search engines.'}
                </p>
              </div>
            )}
          </div>

          {/* SEO Score */}
          <div className="border-t border-gray-200 pt-6">
            <SEOScore
              hasTitle={titleLength >= 30 && titleLength <= MAX_TITLE_LENGTH}
              hasDescription={descriptionLength >= 70 && descriptionLength <= MAX_DESCRIPTION_LENGTH}
              hasKeywords={metaKeywords.length > 0}
              hasOgImage={ogImage.length > 0}
            />
          </div>
        </CardContent>
      )}
    </Card>
  )
}

function SEOScore({ hasTitle, hasDescription, hasKeywords, hasOgImage }) {
  const checks = [
    { label: 'Meta title optimized', passed: hasTitle },
    { label: 'Meta description optimized', passed: hasDescription },
    { label: 'Keywords added', passed: hasKeywords },
    { label: 'Social image set', passed: hasOgImage },
  ]

  const passedCount = checks.filter((c) => c.passed).length
  const score = Math.round((passedCount / checks.length) * 100)

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <span className="font-medium text-gray-900">SEO Score</span>
        <span className={`text-lg font-bold ${
          score >= 75 ? 'text-green-600' : score >= 50 ? 'text-yellow-600' : 'text-red-600'
        }`}>
          {score}%
        </span>
      </div>
      <div className="h-2 bg-gray-200 rounded-full overflow-hidden mb-4">
        <div
          className={`h-full transition-all ${
            score >= 75 ? 'bg-green-500' : score >= 50 ? 'bg-yellow-500' : 'bg-red-500'
          }`}
          style={{ width: `${score}%` }}
        />
      </div>
      <div className="space-y-2">
        {checks.map((check, i) => (
          <div key={i} className="flex items-center gap-2 text-sm">
            {check.passed ? (
              <CheckCircle className="h-4 w-4 text-green-500" />
            ) : (
              <AlertCircle className="h-4 w-4 text-gray-300" />
            )}
            <span className={check.passed ? 'text-gray-700' : 'text-gray-400'}>
              {check.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default SEOPanel
