import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { rolesApi, analyticsApi } from '../../services/api'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card'
import {
  Shield,
  Users,
  FileText,
  Image,
  Settings,
  RefreshCw,
  AlertCircle,
  Check,
  X,
} from 'lucide-react'
import Button from '../../components/ui/Button'

// Permission groups define what capabilities exist in the system
const permissionGroups = [
  {
    name: 'Content',
    icon: FileText,
    permissions: [
      { key: 'content.view', label: 'View Content' },
      { key: 'content.create', label: 'Create Content' },
      { key: 'content.edit', label: 'Edit Content' },
      { key: 'content.delete', label: 'Delete Content' },
      { key: 'content.publish', label: 'Publish Content' },
    ],
  },
  {
    name: 'Users',
    icon: Users,
    permissions: [
      { key: 'users.view', label: 'View Users' },
      { key: 'users.create', label: 'Create Users' },
      { key: 'users.edit', label: 'Edit Users' },
      { key: 'users.delete', label: 'Delete Users' },
      { key: 'users.manage_roles', label: 'Manage Roles' },
    ],
  },
  {
    name: 'Media',
    icon: Image,
    permissions: [
      { key: 'media.view', label: 'View Media' },
      { key: 'media.upload', label: 'Upload Media' },
      { key: 'media.delete', label: 'Delete Media' },
    ],
  },
  {
    name: 'Settings',
    icon: Settings,
    permissions: [
      { key: 'settings.view', label: 'View Settings' },
      { key: 'settings.edit', label: 'Edit Settings' },
      { key: 'settings.api_keys', label: 'Manage API Keys' },
      { key: 'settings.webhooks', label: 'Manage Webhooks' },
    ],
  },
]

// Predefined roles with their permissions (matching backend RoleEnum)
const roleDefinitions = {
  superadmin: {
    name: 'Super Admin',
    description: 'Full system access with all permissions',
    color: '#EF4444',
    hierarchy: 5,
    permissions: permissionGroups.flatMap((g) => g.permissions.map((p) => p.key)),
  },
  admin: {
    name: 'Admin',
    description: 'Administrative access to manage users and content',
    color: '#F59E0B',
    hierarchy: 4,
    permissions: [
      'content.view', 'content.create', 'content.edit', 'content.delete', 'content.publish',
      'users.view', 'users.create', 'users.edit', 'users.delete',
      'media.view', 'media.upload', 'media.delete',
      'settings.view',
    ],
  },
  manager: {
    name: 'Manager',
    description: 'Can manage content and view analytics',
    color: '#8B5CF6',
    hierarchy: 3,
    permissions: [
      'content.view', 'content.create', 'content.edit', 'content.delete', 'content.publish',
      'users.view',
      'media.view', 'media.upload', 'media.delete',
    ],
  },
  editor: {
    name: 'Editor',
    description: 'Can create, edit, and publish content',
    color: '#10B981',
    hierarchy: 2,
    permissions: [
      'content.view', 'content.create', 'content.edit', 'content.publish',
      'media.view', 'media.upload',
    ],
  },
  user: {
    name: 'User',
    description: 'Basic user with read access',
    color: '#6B7280',
    hierarchy: 1,
    permissions: ['content.view', 'media.view'],
  },
}

function RolesPage() {
  const [selectedRoleKey, setSelectedRoleKey] = useState(null)

  // Fetch available roles from backend
  const { data: roleNames = [], isLoading: rolesLoading, error: rolesError, refetch } = useQuery({
    queryKey: ['roles'],
    queryFn: async () => {
      const response = await rolesApi.getAll()
      return response.data || []
    },
  })

  // Fetch user statistics to get user counts per role
  const { data: userStats } = useQuery({
    queryKey: ['analytics', 'users'],
    queryFn: async () => {
      const response = await analyticsApi.getUserStats()
      return response.data
    },
  })

  // Build roles list with definitions and user counts
  const roles = roleNames.map((roleName) => {
    const definition = roleDefinitions[roleName] || {
      name: roleName.charAt(0).toUpperCase() + roleName.slice(1),
      description: 'System role',
      color: '#6B7280',
      hierarchy: 0,
      permissions: [],
    }

    // Get user count from stats (users_by_role is keyed by role_id, need to map)
    const userCount = userStats?.users_by_role?.[roleName] || 0

    return {
      key: roleName,
      ...definition,
      userCount,
    }
  }).sort((a, b) => b.hierarchy - a.hierarchy)

  const selectedRole = roles.find((r) => r.key === selectedRoleKey)

  if (rolesError) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <AlertCircle className="h-12 w-12 text-red-500 mb-4" />
        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">Failed to load roles</h3>
        <p className="text-gray-500 dark:text-gray-400 mt-1">{rolesError.message}</p>
        <Button onClick={() => refetch()} className="mt-4">
          <RefreshCw className="h-4 w-4 mr-2" />
          Try Again
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Roles & Permissions</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">View system roles and their permissions</p>
        </div>
        <Button variant="outline" onClick={() => refetch()} disabled={rolesLoading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${rolesLoading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Roles list */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              System Roles
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {rolesLoading ? (
              <div className="p-6 space-y-3">
                {[1, 2, 3, 4, 5].map((i) => (
                  <div key={i} className="h-14 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
                ))}
              </div>
            ) : roles.length > 0 ? (
              <div className="divide-y divide-gray-200 dark:divide-gray-700">
                {roles.map((role) => (
                  <button
                    key={role.key}
                    onClick={() => setSelectedRoleKey(role.key)}
                    className={`w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors ${
                      selectedRoleKey === role.key ? 'bg-primary-50 dark:bg-primary-900/30' : ''
                    }`}
                  >
                    <div
                      className="h-3 w-3 rounded-full flex-shrink-0"
                      style={{ backgroundColor: role.color }}
                    />
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-gray-900 dark:text-gray-100">{role.name}</p>
                      <p className="text-sm text-gray-500 dark:text-gray-400 truncate">{role.description}</p>
                    </div>
                    <span className="text-sm text-gray-400">{role.userCount} users</span>
                  </button>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 dark:text-gray-400 text-center py-8">No roles found</p>
            )}
          </CardContent>
        </Card>

        {/* Role details */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>
              {selectedRole ? 'Role Details' : 'Select a Role'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {selectedRole ? (
              <div className="space-y-6">
                {/* Role info */}
                <div className="flex items-start gap-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                  <div
                    className="h-12 w-12 rounded-lg flex items-center justify-center flex-shrink-0"
                    style={{ backgroundColor: selectedRole.color + '20' }}
                  >
                    <Shield className="h-6 w-6" style={{ color: selectedRole.color }} />
                  </div>
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">{selectedRole.name}</h3>
                    <p className="text-gray-500 dark:text-gray-400">{selectedRole.description}</p>
                    <div className="flex items-center gap-4 mt-2 text-sm">
                      <span className="text-gray-500 dark:text-gray-400">
                        <Users className="h-4 w-4 inline mr-1" />
                        {selectedRole.userCount} users
                      </span>
                      <span className="text-gray-500 dark:text-gray-400">
                        Hierarchy Level: {selectedRole.hierarchy}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Permissions */}
                <div>
                  <h4 className="font-medium text-gray-900 dark:text-gray-100 mb-4">Permissions</h4>
                  <div className="space-y-4">
                    {permissionGroups.map((group) => {
                      const GroupIcon = group.icon
                      const groupPermissions = group.permissions.map((p) => p.key)
                      const selectedCount = groupPermissions.filter((p) =>
                        selectedRole.permissions.includes(p)
                      ).length

                      return (
                        <div key={group.name} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                          <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center gap-2">
                              <GroupIcon className="h-5 w-5 text-gray-500 dark:text-gray-400" />
                              <span className="font-medium text-gray-900 dark:text-gray-100">{group.name}</span>
                              <span className="text-sm text-gray-500 dark:text-gray-400">
                                ({selectedCount}/{groupPermissions.length})
                              </span>
                            </div>
                          </div>
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                            {group.permissions.map((permission) => {
                              const hasPermission = selectedRole.permissions.includes(permission.key)
                              return (
                                <div
                                  key={permission.key}
                                  className={`flex items-center gap-2 p-2 rounded-lg ${
                                    hasPermission
                                      ? 'bg-green-50 dark:bg-green-900/30'
                                      : 'bg-gray-50 dark:bg-gray-800'
                                  }`}
                                >
                                  {hasPermission ? (
                                    <Check className="h-4 w-4 text-green-600 dark:text-green-400" />
                                  ) : (
                                    <X className="h-4 w-4 text-gray-400" />
                                  )}
                                  <span className={`text-sm ${
                                    hasPermission
                                      ? 'text-green-700 dark:text-green-300'
                                      : 'text-gray-500 dark:text-gray-400'
                                  }`}>
                                    {permission.label}
                                  </span>
                                </div>
                              )
                            })}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>

                {/* Note about role management */}
                <div className="p-4 bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 rounded-lg">
                  <p className="text-sm text-blue-700 dark:text-blue-300">
                    <strong>Note:</strong> System roles are predefined and cannot be modified.
                    Permissions are enforced at the application level. To change a user's access level,
                    update their role assignment in the Users management page.
                  </p>
                </div>
              </div>
            ) : (
              <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                <Shield className="h-12 w-12 mx-auto mb-4 text-gray-300 dark:text-gray-600" />
                <p>Select a role from the list to view its permissions</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default RolesPage
