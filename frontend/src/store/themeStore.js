import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useThemeStore = create(
  persist(
    (set, get) => ({
      theme: 'light', // 'light', 'dark', or 'system'

      // Get the actual theme based on system preference if 'system' is selected
      getEffectiveTheme: () => {
        const { theme } = get()
        if (theme === 'system') {
          return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
        }
        return theme
      },

      // Set theme and update document class
      setTheme: (newTheme) => {
        set({ theme: newTheme })
        const effectiveTheme = newTheme === 'system'
          ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
          : newTheme

        if (effectiveTheme === 'dark') {
          document.documentElement.classList.add('dark')
        } else {
          document.documentElement.classList.remove('dark')
        }
      },

      // Toggle between light and dark (ignoring system)
      toggleTheme: () => {
        const { theme, setTheme } = get()
        const newTheme = theme === 'dark' ? 'light' : 'dark'
        setTheme(newTheme)
      },

      // Initialize theme on app load
      initializeTheme: () => {
        const { theme } = get()
        const effectiveTheme = theme === 'system'
          ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
          : theme

        if (effectiveTheme === 'dark') {
          document.documentElement.classList.add('dark')
        } else {
          document.documentElement.classList.remove('dark')
        }

        // Listen for system theme changes
        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
        const handleChange = (e) => {
          if (get().theme === 'system') {
            if (e.matches) {
              document.documentElement.classList.add('dark')
            } else {
              document.documentElement.classList.remove('dark')
            }
          }
        }
        mediaQuery.addEventListener('change', handleChange)

        return () => mediaQuery.removeEventListener('change', handleChange)
      },
    }),
    {
      name: 'theme-storage',
      partialize: (state) => ({ theme: state.theme }),
    }
  )
)

// Initialize theme on module load
if (typeof window !== 'undefined') {
  useThemeStore.getState().initializeTheme()
}

export default useThemeStore
