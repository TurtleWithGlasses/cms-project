import { useEffect, useState, useCallback } from 'react'
import { X, Command, Keyboard } from 'lucide-react'

const shortcuts = [
  {
    category: 'Navigation',
    items: [
      { keys: ['Ctrl', 'K'], description: 'Open global search' },
      { keys: ['Ctrl', 'D'], description: 'Go to dashboard' },
      { keys: ['Ctrl', 'Shift', 'C'], description: 'Go to content' },
      { keys: ['Ctrl', 'Shift', 'M'], description: 'Go to media' },
      { keys: ['Ctrl', ','], description: 'Open settings' },
      { keys: ['?'], description: 'Show keyboard shortcuts' },
    ],
  },
  {
    category: 'Content Editing',
    items: [
      { keys: ['Ctrl', 'S'], description: 'Save content' },
      { keys: ['Ctrl', 'Shift', 'S'], description: 'Save and publish' },
      { keys: ['Ctrl', 'Enter'], description: 'Submit form' },
      { keys: ['Ctrl', 'Z'], description: 'Undo' },
      { keys: ['Ctrl', 'Shift', 'Z'], description: 'Redo' },
      { keys: ['Ctrl', 'B'], description: 'Bold text' },
      { keys: ['Ctrl', 'I'], description: 'Italic text' },
      { keys: ['Ctrl', 'U'], description: 'Underline text' },
    ],
  },
  {
    category: 'Lists & Tables',
    items: [
      { keys: ['Ctrl', 'A'], description: 'Select all items' },
      { keys: ['Shift', 'Click'], description: 'Select range' },
      { keys: ['Ctrl', 'Click'], description: 'Toggle item selection' },
      { keys: ['Delete'], description: 'Delete selected items' },
      { keys: ['Escape'], description: 'Clear selection' },
    ],
  },
  {
    category: 'General',
    items: [
      { keys: ['Escape'], description: 'Close modal / Cancel action' },
      { keys: ['Ctrl', 'N'], description: 'Create new item' },
      { keys: ['Ctrl', '/'], description: 'Toggle sidebar' },
      { keys: ['F11'], description: 'Toggle fullscreen' },
    ],
  },
]

function KeyboardShortcutsModal({ isOpen, onClose }) {
  const [isMac, setIsMac] = useState(false)

  useEffect(() => {
    setIsMac(navigator.platform.toUpperCase().indexOf('MAC') >= 0)
  }, [])

  // Close on Escape
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  const formatKey = (key) => {
    if (isMac) {
      if (key === 'Ctrl') return '⌘'
      if (key === 'Alt') return '⌥'
      if (key === 'Shift') return '⇧'
    }
    return key
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="min-h-screen px-4 text-center">
        {/* Backdrop */}
        <div
          className="fixed inset-0 bg-black/50 transition-opacity"
          onClick={onClose}
        />

        {/* Modal */}
        <div className="inline-block w-full max-w-2xl my-8 text-left align-middle bg-white dark:bg-gray-800 rounded-xl shadow-xl transform transition-all">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 bg-primary-100 dark:bg-primary-900/50 rounded-lg flex items-center justify-center">
                <Keyboard className="h-5 w-5 text-primary-600 dark:text-primary-400" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Keyboard Shortcuts</h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {isMac ? 'Showing shortcuts for Mac' : 'Showing shortcuts for Windows/Linux'}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
            >
              <X className="h-5 w-5 text-gray-400" />
            </button>
          </div>

          {/* Content */}
          <div className="px-6 py-4 max-h-[60vh] overflow-y-auto">
            <div className="space-y-6">
              {shortcuts.map((section) => (
                <div key={section.category}>
                  <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100 uppercase tracking-wider mb-3">
                    {section.category}
                  </h4>
                  <div className="space-y-2">
                    {section.items.map((shortcut, index) => (
                      <div
                        key={index}
                        className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
                      >
                        <span className="text-sm text-gray-600 dark:text-gray-400">{shortcut.description}</span>
                        <div className="flex items-center gap-1">
                          {shortcut.keys.map((key, keyIndex) => (
                            <span key={keyIndex} className="flex items-center">
                              <kbd className="inline-flex items-center justify-center min-w-[28px] h-7 px-2 bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded text-xs font-medium text-gray-700 dark:text-gray-300 shadow-sm">
                                {formatKey(key)}
                              </kbd>
                              {keyIndex < shortcut.keys.length - 1 && (
                                <span className="mx-1 text-gray-400">+</span>
                              )}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Footer */}
          <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 rounded-b-xl">
            <p className="text-sm text-gray-500 dark:text-gray-400 text-center">
              Press <kbd className="inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded text-xs font-medium text-gray-700 dark:text-gray-300">?</kbd> anywhere to open this dialog
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

// Hook for handling keyboard shortcuts
export function useKeyboardShortcuts(shortcuts = {}) {
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Don't trigger if user is typing in an input
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable) {
        return
      }

      const key = e.key.toLowerCase()
      const ctrl = e.ctrlKey || e.metaKey
      const shift = e.shiftKey
      const alt = e.altKey

      // Build shortcut string
      let shortcutKey = ''
      if (ctrl) shortcutKey += 'ctrl+'
      if (shift) shortcutKey += 'shift+'
      if (alt) shortcutKey += 'alt+'
      shortcutKey += key

      if (shortcuts[shortcutKey]) {
        e.preventDefault()
        shortcuts[shortcutKey]()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [shortcuts])
}

// Provider component for global shortcuts
export function KeyboardShortcutsProvider({ children }) {
  const [isOpen, setIsOpen] = useState(false)

  const handleKeyDown = useCallback((e) => {
    // Don't trigger if user is typing in an input
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable) {
      return
    }

    // ? key opens shortcuts modal
    if (e.key === '?' && !e.ctrlKey && !e.metaKey) {
      e.preventDefault()
      setIsOpen(true)
    }
  }, [])

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  return (
    <>
      {children}
      <KeyboardShortcutsModal isOpen={isOpen} onClose={() => setIsOpen(false)} />
    </>
  )
}

export default KeyboardShortcutsModal
