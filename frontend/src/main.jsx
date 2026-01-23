import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import { ToastProvider } from './components/ui/Toast'
import { KeyboardShortcutsProvider } from './components/ui/KeyboardShortcutsModal'
import { useThemeStore } from './store/themeStore'
import './index.css'

// Initialize theme before rendering to prevent flash
useThemeStore.getState().initializeTheme()

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ToastProvider>
          <KeyboardShortcutsProvider>
            <App />
          </KeyboardShortcutsProvider>
        </ToastProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
)
