import { createContext, useContext, useState, useCallback } from 'react'
import { CheckCircle, XCircle, AlertCircle, Info, X } from 'lucide-react'

const ToastContext = createContext(null)

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])

  const addToast = useCallback((message, type = 'info', duration = 5000) => {
    const id = Date.now() + Math.random()
    setToasts((prev) => [...prev, { id, message, type }])

    if (duration > 0) {
      setTimeout(() => {
        removeToast(id)
      }, duration)
    }

    return id
  }, [])

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id))
  }, [])

  const toast = {
    success: (message, duration) => addToast(message, 'success', duration),
    error: (message, duration) => addToast(message, 'error', duration),
    warning: (message, duration) => addToast(message, 'warning', duration),
    info: (message, duration) => addToast(message, 'info', duration),
  }

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <ToastContainer toasts={toasts} removeToast={removeToast} />
    </ToastContext.Provider>
  )
}

export function useToast() {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider')
  }
  return context
}

function ToastContainer({ toasts, removeToast }) {
  if (toasts.length === 0) return null

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onClose={() => removeToast(toast.id)} />
      ))}
    </div>
  )
}

function ToastItem({ toast, onClose }) {
  const { message, type } = toast

  const styles = {
    success: {
      bg: 'bg-green-50 border-green-200 dark:bg-green-900/50 dark:border-green-800',
      icon: <CheckCircle className="h-5 w-5 text-green-500 dark:text-green-400" />,
      text: 'text-green-800 dark:text-green-200',
    },
    error: {
      bg: 'bg-red-50 border-red-200 dark:bg-red-900/50 dark:border-red-800',
      icon: <XCircle className="h-5 w-5 text-red-500 dark:text-red-400" />,
      text: 'text-red-800 dark:text-red-200',
    },
    warning: {
      bg: 'bg-yellow-50 border-yellow-200 dark:bg-yellow-900/50 dark:border-yellow-800',
      icon: <AlertCircle className="h-5 w-5 text-yellow-500 dark:text-yellow-400" />,
      text: 'text-yellow-800 dark:text-yellow-200',
    },
    info: {
      bg: 'bg-blue-50 border-blue-200 dark:bg-blue-900/50 dark:border-blue-800',
      icon: <Info className="h-5 w-5 text-blue-500 dark:text-blue-400" />,
      text: 'text-blue-800 dark:text-blue-200',
    },
  }

  const style = styles[type] || styles.info

  return (
    <div
      className={`flex items-center gap-3 px-4 py-3 rounded-lg border shadow-lg min-w-[300px] max-w-md animate-slide-in ${style.bg}`}
    >
      {style.icon}
      <p className={`flex-1 text-sm ${style.text}`}>{message}</p>
      <button
        onClick={onClose}
        className="p-1 hover:bg-white/50 dark:hover:bg-black/30 rounded"
      >
        <X className="h-4 w-4 text-gray-500 dark:text-gray-400" />
      </button>
    </div>
  )
}

export default ToastProvider
