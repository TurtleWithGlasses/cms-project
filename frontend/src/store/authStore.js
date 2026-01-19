import { create } from 'zustand'
import { authApi } from '../services/api'

export const useAuthStore = create((set, get) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,
  requires2FA: false,
  tempToken: null,

  // Initialize auth state from localStorage
  initialize: async () => {
    const token = localStorage.getItem('access_token')
    if (token) {
      try {
        const response = await authApi.getProfile()
        set({
          user: response.data,
          isAuthenticated: true,
          isLoading: false,
        })
      } catch (error) {
        localStorage.removeItem('access_token')
        set({ isAuthenticated: false, isLoading: false, user: null })
      }
    } else {
      set({ isLoading: false })
    }
  },

  // Login
  login: async (email, password) => {
    try {
      const response = await authApi.login(email, password)
      const { access_token, requires_2fa, temp_token } = response.data

      if (requires_2fa) {
        set({ requires2FA: true, tempToken: temp_token })
        return { requires2FA: true }
      }

      localStorage.setItem('access_token', access_token)

      // Fetch user profile
      const profileResponse = await authApi.getProfile()
      set({
        user: profileResponse.data,
        isAuthenticated: true,
        requires2FA: false,
        tempToken: null,
      })

      return { success: true }
    } catch (error) {
      throw error.response?.data?.detail || 'Login failed'
    }
  },

  // Verify 2FA
  verify2FA: async (code) => {
    try {
      const { tempToken } = get()
      const response = await authApi.verify2FA(code)
      const { access_token } = response.data

      localStorage.setItem('access_token', access_token)

      // Fetch user profile
      const profileResponse = await authApi.getProfile()
      set({
        user: profileResponse.data,
        isAuthenticated: true,
        requires2FA: false,
        tempToken: null,
      })

      return { success: true }
    } catch (error) {
      throw error.response?.data?.detail || '2FA verification failed'
    }
  },

  // Register
  register: async (data) => {
    try {
      await authApi.register(data)
      return { success: true }
    } catch (error) {
      throw error.response?.data?.detail || 'Registration failed'
    }
  },

  // Logout
  logout: () => {
    localStorage.removeItem('access_token')
    set({
      user: null,
      isAuthenticated: false,
      requires2FA: false,
      tempToken: null,
    })
  },

  // Update user data
  updateUser: (userData) => {
    set({ user: { ...get().user, ...userData } })
  },
}))

// Initialize auth on app load
useAuthStore.getState().initialize()

export default useAuthStore
