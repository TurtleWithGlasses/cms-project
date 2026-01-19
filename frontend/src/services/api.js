import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor to handle errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Auth API
export const authApi = {
  login: (email, password) =>
    axios.post('/auth/token', new URLSearchParams({ username: email, password }), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    }),
  register: (data) => axios.post('/auth/register', data),
  verify2FA: (code) => api.post('/two-factor/verify', { code }),
  getProfile: () => api.get('/users/me'),
}

// Dashboard API
export const dashboardApi = {
  getSummary: (periodDays = 30) => api.get(`/dashboard/summary?period_days=${periodDays}`),
  getContentKPIs: (periodDays = 30) => api.get(`/dashboard/kpis/content?period_days=${periodDays}`),
  getUserKPIs: (periodDays = 30) => api.get(`/dashboard/kpis/users?period_days=${periodDays}`),
  getSystemHealth: () => api.get('/dashboard/system-health'),
  getMyActivity: (periodDays = 7) => api.get(`/dashboard/my-activity?period_days=${periodDays}`),
}

// Content API
export const contentApi = {
  getAll: (params = {}) => api.get('/content', { params }),
  getById: (id) => api.get(`/content/${id}`),
  create: (data) => api.post('/content', data),
  update: (id, data) => api.put(`/content/${id}`, data),
  delete: (id) => api.delete(`/content/${id}`),
  publish: (id) => api.post(`/content/${id}/publish`),
  unpublish: (id) => api.post(`/content/${id}/unpublish`),
}

// Users API
export const usersApi = {
  getAll: (params = {}) => api.get('/users', { params }),
  getById: (id) => api.get(`/users/${id}`),
  create: (data) => api.post('/users', data),
  update: (id, data) => api.put(`/users/${id}`, data),
  delete: (id) => api.delete(`/users/${id}`),
  updateRole: (id, roleId) => api.put(`/users/${id}/role`, { role_id: roleId }),
}

// Categories API
export const categoriesApi = {
  getAll: (params = {}) => api.get('/categories', { params }),
  getById: (id) => api.get(`/categories/${id}`),
  create: (data) => api.post('/categories', data),
  update: (id, data) => api.put(`/categories/${id}`, data),
  delete: (id) => api.delete(`/categories/${id}`),
}

// Tags API
export const tagsApi = {
  getAll: (params = {}) => api.get('/tags', { params }),
  getById: (id) => api.get(`/tags/${id}`),
  create: (data) => api.post('/tags', data),
  update: (id, data) => api.put(`/tags/${id}`, data),
  delete: (id) => api.delete(`/tags/${id}`),
}

// Comments API
export const commentsApi = {
  getAll: (params = {}) => api.get('/comments', { params }),
  getById: (id) => api.get(`/comments/${id}`),
  approve: (id) => api.post(`/comments/${id}/approve`),
  reject: (id) => api.post(`/comments/${id}/reject`),
  delete: (id) => api.delete(`/comments/${id}`),
}

// Media API
export const mediaApi = {
  getAll: (params = {}) => api.get('/media', { params }),
  upload: (file, onProgress) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: onProgress,
    })
  },
  delete: (id) => api.delete(`/media/${id}`),
}

// Teams API
export const teamsApi = {
  getAll: (params = {}) => api.get('/teams', { params }),
  getById: (id) => api.get(`/teams/${id}`),
  create: (data) => api.post('/teams', data),
  update: (id, data) => api.put(`/teams/${id}`, data),
  delete: (id) => api.delete(`/teams/${id}`),
  getMembers: (teamId) => api.get(`/teams/${teamId}/members`),
  addMember: (teamId, data) => api.post(`/teams/${teamId}/members`, data),
  removeMember: (teamId, userId) => api.delete(`/teams/${teamId}/members/${userId}`),
  inviteMember: (teamId, data) => api.post(`/teams/${teamId}/invitations`, data),
}

// Notifications API
export const notificationsApi = {
  getAll: () => api.get('/notifications'),
  getUnreadCount: () => api.get('/notifications/unread-count'),
  markAsRead: (id) => api.post(`/notifications/${id}/read`),
  markAllAsRead: () => api.post('/notifications/read-all'),
}

export default api
