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
  register: (data) => api.post('/users/register', data),
  verify2FA: (code) => api.post('/two-factor/verify', { code }),
  getProfile: () => api.get('/users/me'),
  forgotPassword: (email) => api.post('/password-reset/request', { email }),
  resetPassword: (token, password) => api.post('/password-reset/reset', { token, password }),
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

// API Keys API
export const apiKeysApi = {
  getAll: () => api.get('/api-keys'),
  create: (data) => api.post('/api-keys', data),
  delete: (id) => api.delete(`/api-keys/${id}`),
}

// Webhooks API
export const webhooksApi = {
  getAll: () => api.get('/webhooks'),
  getById: (id) => api.get(`/webhooks/${id}`),
  create: (data) => api.post('/webhooks', data),
  update: (id, data) => api.put(`/webhooks/${id}`, data),
  delete: (id) => api.delete(`/webhooks/${id}`),
  test: (id) => api.post(`/webhooks/${id}/test`),
}

// Templates API
export const templatesApi = {
  getAll: (params = {}) => api.get('/templates', { params }),
  getById: (id) => api.get(`/templates/${id}`),
  create: (data) => api.post('/templates', data),
  update: (id, data) => api.put(`/templates/${id}`, data),
  delete: (id) => api.delete(`/templates/${id}`),
  duplicate: (id) => api.post(`/templates/${id}/duplicate`),
}

// Activity API
export const activityApi = {
  getAll: (params = {}) => api.get('/activity', { params }),
  getByResource: (resourceType, resourceId) =>
    api.get(`/activity/${resourceType}/${resourceId}`),
  exportLogs: (params = {}) => api.get('/activity/export', { params, responseType: 'blob' }),
}

// Search API
export const searchApi = {
  global: (query, params = {}) => api.get('/search', { params: { q: query, ...params } }),
  content: (query, params = {}) => api.get('/search/content', { params: { q: query, ...params } }),
  users: (query, params = {}) => api.get('/search/users', { params: { q: query, ...params } }),
  media: (query, params = {}) => api.get('/search/media', { params: { q: query, ...params } }),
}

// Roles API
export const rolesApi = {
  getAll: () => api.get('/roles'),
  getById: (id) => api.get(`/roles/${id}`),
  create: (data) => api.post('/roles', data),
  update: (id, data) => api.put(`/roles/${id}`, data),
  delete: (id) => api.delete(`/roles/${id}`),
  getPermissions: () => api.get('/roles/permissions'),
}

// Import/Export API
export const importExportApi = {
  export: (options) => api.post('/export', options, { responseType: 'blob' }),
  import: (formData) => api.post('/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  preview: (formData) => api.post('/import/preview', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
}

// Analytics API
export const analyticsApi = {
  getDashboard: () => api.get('/analytics/dashboard'),
  getContentStats: () => api.get('/analytics/content'),
  getUserStats: () => api.get('/analytics/users'),
  getActivityStats: (days = 30) => api.get(`/analytics/activity?days=${days}`),
  getMediaStats: () => api.get('/analytics/media'),
  getMyPerformance: () => api.get('/analytics/my-performance'),
  getUserPerformance: (userId) => api.get(`/analytics/user/${userId}/performance`),
  getPopularContent: (days = 30, limit = 10) => api.get('/analytics/content/popular', { params: { days, limit } }),
  getContentViews: (contentId, days = 30) => api.get(`/analytics/content/${contentId}/views`, { params: { days } }),
  getSessionAnalytics: (days = 30) => api.get('/analytics/sessions', { params: { days } }),
}

// Monitoring API - Note: health endpoints are at root level, not under /monitoring
export const monitoringApi = {
  getHealth: () => axios.get('/health'),
  getReadiness: () => axios.get('/ready'),
  getDetailedHealth: () => axios.get('/health/detailed'),
  getMetrics: () => axios.get('/metrics'),
  getMetricsSummary: () => axios.get('/metrics/summary'),
}

// Workflow API
export const workflowApi = {
  getPending: (params = {}) => api.get('/workflow/pending', { params }),
  approve: (id, data) => api.post(`/workflow/${id}/approve`, data),
  reject: (id, data) => api.post(`/workflow/${id}/reject`, data),
  requestChanges: (id, data) => api.post(`/workflow/${id}/request-changes`, data),
  getHistory: (contentId) => api.get(`/workflow/${contentId}/history`),
}

// SEO API
export const seoApi = {
  getByContent: (contentId) => api.get(`/seo/content/${contentId}`),
  update: (contentId, data) => api.put(`/seo/content/${contentId}`, data),
  analyze: (contentId) => api.get(`/seo/content/${contentId}/analyze`),
  getSitemap: () => api.get('/seo/sitemap'),
  getRobotsTxt: () => api.get('/seo/robots.txt'),
}

// Revisions API
export const revisionsApi = {
  getByContent: (contentId, params = {}) => api.get(`/content/${contentId}/revisions`, { params }),
  getById: (contentId, revisionId) => api.get(`/content/${contentId}/revisions/${revisionId}`),
  restore: (contentId, revisionId) => api.post(`/content/${contentId}/revisions/${revisionId}/restore`),
  compare: (contentId, revisionId1, revisionId2) =>
    api.get(`/content/${contentId}/revisions/compare`, { params: { from: revisionId1, to: revisionId2 } }),
}

// Privacy API
export const privacyApi = {
  getSettings: () => api.get('/privacy/settings'),
  updateSettings: (data) => api.put('/privacy/settings', data),
  getCookieConfig: () => api.get('/privacy/cookies'),
  updateCookieConfig: (data) => api.put('/privacy/cookies', data),
  getDataRetention: () => api.get('/privacy/data-retention'),
  updateDataRetention: (data) => api.put('/privacy/data-retention', data),
  exportUserData: (userId) => api.get(`/privacy/users/${userId}/export`, { responseType: 'blob' }),
  deleteUserData: (userId) => api.delete(`/privacy/users/${userId}/data`),
  getConsentLogs: (params = {}) => api.get('/privacy/consent-logs', { params }),
}

// Cache API
export const cacheApi = {
  getStats: () => api.get('/cache/stats'),
  getCaches: () => api.get('/cache'),
  clear: (cacheKey) => api.delete(`/cache/${cacheKey}`),
  clearAll: () => api.delete('/cache'),
  warmup: (cacheKey) => api.post(`/cache/${cacheKey}/warmup`),
  getActivity: (params = {}) => api.get('/cache/activity', { params }),
}

// Bulk Actions API
export const bulkActionsApi = {
  publish: (ids) => api.post('/content/bulk/publish', { content_ids: ids }),
  updateStatus: (ids, status) => api.post('/content/bulk/update-status', { content_ids: ids, status }),
  delete: (ids) => api.post('/content/bulk/delete', { content_ids: ids }),
  updateCategory: (ids, categoryId) => api.post('/content/bulk/update-category', { content_ids: ids, category_id: categoryId }),
  assignTags: (ids, tagIds) => api.post('/content/bulk/assign-tags', { content_ids: ids, tag_ids: tagIds }),
  updateUserRoles: (userIds, roleId) => api.post('/users/bulk/update-roles', { user_ids: userIds, role_id: roleId }),
}

// Two Factor API
export const twoFactorApi = {
  getStatus: () => api.get('/2fa/status'),
  setup: (method) => api.post('/2fa/setup', { method }),
  verify: (code) => api.post('/2fa/verify', { code }),
  disable: (code) => api.post('/2fa/disable', { code }),
  regenerateBackupCodes: () => api.post('/2fa/backup-codes/regenerate'),
}

// Site Settings API
export const siteSettingsApi = {
  get: () => api.get('/settings/site'),
  update: (data) => api.put('/settings/site', data),
  uploadLogo: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/settings/site/logo', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  uploadFavicon: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/settings/site/favicon', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}

// Localization API
export const localizationApi = {
  getLanguages: () => api.get('/localization/languages'),
  addLanguage: (code) => api.post('/localization/languages', { code }),
  removeLanguage: (code) => api.delete(`/localization/languages/${code}`),
  setDefault: (code) => api.put(`/localization/languages/${code}/default`),
  toggleEnabled: (code, enabled) => api.put(`/localization/languages/${code}`, { enabled }),
  getTranslations: (lang) => api.get(`/localization/translations/${lang}`),
  updateTranslation: (lang, key, value) => api.put(`/localization/translations/${lang}`, { key, value }),
  exportTranslations: (lang) => api.get(`/localization/translations/${lang}/export`, { responseType: 'blob' }),
  importTranslations: (lang, file) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post(`/localization/translations/${lang}/import`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}

// Backup API
export const backupApi = {
  getAll: () => api.get('/backups'),
  create: (options) => api.post('/backups', options),
  delete: (id) => api.delete(`/backups/${id}`),
  download: (id) => api.get(`/backups/${id}/download`, { responseType: 'blob' }),
  restore: (id) => api.post(`/backups/${id}/restore`),
  getSchedule: () => api.get('/backups/schedule'),
  updateSchedule: (data) => api.put('/backups/schedule', data),
  getStorageInfo: () => api.get('/backups/storage'),
}

// Email Templates API
export const emailTemplatesApi = {
  getAll: () => api.get('/email-templates'),
  getById: (id) => api.get(`/email-templates/${id}`),
  update: (id, data) => api.put(`/email-templates/${id}`, data),
  sendTest: (id, email) => api.post(`/email-templates/${id}/test`, { email }),
  resetToDefault: (id) => api.post(`/email-templates/${id}/reset`),
}

export default api
