import { describe, it, expect, beforeEach, vi } from 'vitest'
import useAuthStore from './authStore'

// Mock the api module
vi.mock('../services/api', () => ({
  authApi: {
    me: vi.fn(),
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    verify2FA: vi.fn(),
  },
}))

describe('authStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useAuthStore.setState({
      user: null,
      isAuthenticated: false,
      isLoading: true,
      requires2FA: false,
      tempToken: null,
    })
    // Clear localStorage
    localStorage.clear()
  })

  it('has correct initial state', () => {
    const state = useAuthStore.getState()
    expect(state.user).toBeNull()
    expect(state.isAuthenticated).toBe(false)
    expect(state.isLoading).toBe(true)
    expect(state.requires2FA).toBe(false)
  })

  it('logout clears user and token', () => {
    // Set up authenticated state
    useAuthStore.setState({
      user: { id: 1, username: 'test' },
      isAuthenticated: true,
    })
    localStorage.setItem('token', 'test-token')

    // Call logout
    useAuthStore.getState().logout()

    // Verify state is cleared
    const state = useAuthStore.getState()
    expect(state.user).toBeNull()
    expect(state.isAuthenticated).toBe(false)
    expect(localStorage.getItem('token')).toBeNull()
  })

  it('setRequires2FA updates state correctly', () => {
    useAuthStore.getState().setRequires2FA(true, 'temp-token')

    const state = useAuthStore.getState()
    expect(state.requires2FA).toBe(true)
    expect(state.tempToken).toBe('temp-token')
  })
})
