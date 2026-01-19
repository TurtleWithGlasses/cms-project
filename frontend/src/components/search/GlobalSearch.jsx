import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { searchApi } from '../../services/api'
import {
  Search,
  X,
  FileText,
  User,
  Image,
  Folder,
  Tag,
  Command,
} from 'lucide-react'

function GlobalSearch() {
  const navigate = useNavigate()
  const [isOpen, setIsOpen] = useState(false)
  const [query, setQuery] = useState('')
  const inputRef = useRef(null)
  const containerRef = useRef(null)

  // Keyboard shortcut (Cmd/Ctrl + K)
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setIsOpen(true)
      }
      if (e.key === 'Escape') {
        setIsOpen(false)
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [])

  // Focus input when opened
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus()
    }
  }, [isOpen])

  // Close on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isOpen])

  // Search query
  const { data: results, isLoading } = useQuery({
    queryKey: ['global-search', query],
    queryFn: () => searchApi.global(query),
    select: (res) => res.data,
    enabled: query.length >= 2,
    staleTime: 1000,
  })

  const getIcon = (type) => {
    const icons = {
      content: <FileText className="h-4 w-4" />,
      user: <User className="h-4 w-4" />,
      media: <Image className="h-4 w-4" />,
      category: <Folder className="h-4 w-4" />,
      tag: <Tag className="h-4 w-4" />,
    }
    return icons[type] || <FileText className="h-4 w-4" />
  }

  const handleSelect = (result) => {
    const routes = {
      content: `/content/${result.id}`,
      user: `/users`,
      media: `/media`,
      category: `/categories`,
      tag: `/tags`,
    }
    navigate(routes[result.type] || '/')
    setIsOpen(false)
    setQuery('')
  }

  const groupedResults = results?.reduce((acc, result) => {
    if (!acc[result.type]) acc[result.type] = []
    acc[result.type].push(result)
    return acc
  }, {}) || {}

  const typeLabels = {
    content: 'Content',
    user: 'Users',
    media: 'Media',
    category: 'Categories',
    tag: 'Tags',
  }

  return (
    <>
      {/* Search trigger button */}
      <button
        onClick={() => setIsOpen(true)}
        className="flex items-center gap-2 w-full px-3 py-2 text-sm text-gray-500 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
      >
        <Search className="h-4 w-4" />
        <span className="flex-1 text-left">Search...</span>
        <kbd className="hidden sm:inline-flex items-center gap-1 px-1.5 py-0.5 text-xs font-medium bg-gray-200 text-gray-600 rounded">
          <Command className="h-3 w-3" />K
        </kbd>
      </button>

      {/* Search modal */}
      {isOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="min-h-screen px-4 text-center">
            {/* Backdrop */}
            <div className="fixed inset-0 bg-black/50" />

            {/* Search container */}
            <div
              ref={containerRef}
              className="relative inline-block w-full max-w-xl my-16 text-left bg-white rounded-xl shadow-2xl"
            >
              {/* Search input */}
              <div className="flex items-center gap-3 p-4 border-b border-gray-200">
                <Search className="h-5 w-5 text-gray-400" />
                <input
                  ref={inputRef}
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search content, users, media..."
                  className="flex-1 text-lg outline-none"
                />
                {query && (
                  <button onClick={() => setQuery('')} className="p-1 hover:bg-gray-100 rounded">
                    <X className="h-4 w-4 text-gray-400" />
                  </button>
                )}
              </div>

              {/* Results */}
              <div className="max-h-96 overflow-y-auto">
                {isLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600"></div>
                  </div>
                ) : query.length < 2 ? (
                  <div className="p-4 text-center text-gray-500">
                    <p>Type at least 2 characters to search</p>
                  </div>
                ) : Object.keys(groupedResults).length === 0 ? (
                  <div className="p-8 text-center text-gray-500">
                    <Search className="h-10 w-10 mx-auto mb-3 text-gray-300" />
                    <p>No results found for "{query}"</p>
                  </div>
                ) : (
                  <div className="py-2">
                    {Object.entries(groupedResults).map(([type, items]) => (
                      <div key={type}>
                        <div className="px-4 py-2 text-xs font-medium text-gray-500 uppercase">
                          {typeLabels[type] || type}
                        </div>
                        {items.map((result) => (
                          <button
                            key={`${result.type}-${result.id}`}
                            onClick={() => handleSelect(result)}
                            className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-100 text-left"
                          >
                            <div className="flex-shrink-0 h-8 w-8 bg-gray-100 rounded-lg flex items-center justify-center text-gray-500">
                              {getIcon(result.type)}
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="font-medium text-gray-900 truncate">{result.title}</p>
                              {result.description && (
                                <p className="text-sm text-gray-500 truncate">{result.description}</p>
                              )}
                            </div>
                          </button>
                        ))}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Footer */}
              <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 text-xs text-gray-500">
                <div className="flex items-center gap-4">
                  <span className="flex items-center gap-1">
                    <kbd className="px-1.5 py-0.5 bg-gray-100 rounded">↑↓</kbd>
                    Navigate
                  </span>
                  <span className="flex items-center gap-1">
                    <kbd className="px-1.5 py-0.5 bg-gray-100 rounded">↵</kbd>
                    Select
                  </span>
                </div>
                <span className="flex items-center gap-1">
                  <kbd className="px-1.5 py-0.5 bg-gray-100 rounded">Esc</kbd>
                  Close
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

export default GlobalSearch
