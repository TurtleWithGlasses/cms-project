import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { rolesApi } from '../../services/api'
import { useToast } from '../../components/ui/Toast'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import {
  Shield,
  Plus,
  Edit2,
  Trash2,
  Check,
  X,
  Users,
  FileText,
  Image,
  Settings,
  Eye,
  Pencil,
  UserPlus,
} from 'lucide-react'

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

const defaultRoles = [
  {
    id: 1,
    name: 'Super Admin',
    description: 'Full system access',
    color: '#EF4444',
    userCount: 1,
    permissions: permissionGroups.flatMap((g) => g.permissions.map((p) => p.key)),
  },
  {
    id: 2,
    name: 'Admin',
    description: 'Administrative access without system settings',
    color: '#F59E0B',
    userCount: 3,
    permissions: ['content.view', 'content.create', 'content.edit', 'content.delete', 'content.publish', 'users.view', 'users.create', 'users.edit', 'media.view', 'media.upload', 'media.delete'],
  },
  {
    id: 3,
    name: 'Editor',
    description: 'Can create and edit content',
    color: '#10B981',
    userCount: 8,
    permissions: ['content.view', 'content.create', 'content.edit', 'content.publish', 'media.view', 'media.upload'],
  },
  {
    id: 4,
    name: 'Author',
    description: 'Can create content but cannot publish',
    color: '#3B82F6',
    userCount: 12,
    permissions: ['content.view', 'content.create', 'content.edit', 'media.view', 'media.upload'],
  },
  {
    id: 5,
    name: 'Viewer',
    description: 'Read-only access',
    color: '#6B7280',
    userCount: 25,
    permissions: ['content.view', 'media.view'],
  },
]

function RolesPage() {
  const queryClient = useQueryClient()
  const toast = useToast()
  const [selectedRole, setSelectedRole] = useState(null)
  const [isEditing, setIsEditing] = useState(false)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    color: '#3B82F6',
    permissions: [],
  })

  // In a real app, this would fetch from API
  const { data: roles = defaultRoles, isLoading } = useQuery({
    queryKey: ['roles'],
    queryFn: () => rolesApi.getAll(),
    select: (res) => res.data || defaultRoles,
    placeholderData: defaultRoles,
  })

  const createMutation = useMutation({
    mutationFn: rolesApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['roles'] })
      toast.success('Role created successfully')
      setShowCreateModal(false)
      resetForm()
    },
    onError: () => toast.error('Failed to create role'),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }) => rolesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['roles'] })
      toast.success('Role updated successfully')
      setIsEditing(false)
    },
    onError: () => toast.error('Failed to update role'),
  })

  const deleteMutation = useMutation({
    mutationFn: rolesApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['roles'] })
      toast.success('Role deleted successfully')
      setSelectedRole(null)
    },
    onError: () => toast.error('Failed to delete role'),
  })

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      color: '#3B82F6',
      permissions: [],
    })
  }

  const handleSelectRole = (role) => {
    setSelectedRole(role)
    setFormData({
      name: role.name,
      description: role.description,
      color: role.color,
      permissions: [...role.permissions],
    })
    setIsEditing(false)
  }

  const handlePermissionToggle = (permissionKey) => {
    setFormData((prev) => ({
      ...prev,
      permissions: prev.permissions.includes(permissionKey)
        ? prev.permissions.filter((p) => p !== permissionKey)
        : [...prev.permissions, permissionKey],
    }))
  }

  const handleGroupToggle = (group) => {
    const groupPermissions = group.permissions.map((p) => p.key)
    const allSelected = groupPermissions.every((p) => formData.permissions.includes(p))

    setFormData((prev) => ({
      ...prev,
      permissions: allSelected
        ? prev.permissions.filter((p) => !groupPermissions.includes(p))
        : [...new Set([...prev.permissions, ...groupPermissions])],
    }))
  }

  const handleSave = () => {
    if (selectedRole) {
      updateMutation.mutate({ id: selectedRole.id, data: formData })
    } else {
      createMutation.mutate(formData)
    }
  }

  const handleDelete = () => {
    if (selectedRole && window.confirm(`Delete role "${selectedRole.name}"? Users with this role will need to be reassigned.`)) {
      deleteMutation.mutate(selectedRole.id)
    }
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Roles & Permissions</h1>
          <p className="text-gray-500 mt-1">Manage user roles and their permissions</p>
        </div>
        <Button onClick={() => {
          resetForm()
          setSelectedRole(null)
          setShowCreateModal(true)
        }}>
          <Plus className="h-4 w-4 mr-2" />
          Create Role
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Roles list */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              Roles
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-gray-200">
              {roles.map((role) => (
                <button
                  key={role.id}
                  onClick={() => handleSelectRole(role)}
                  className={`w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-gray-50 transition-colors ${
                    selectedRole?.id === role.id ? 'bg-primary-50' : ''
                  }`}
                >
                  <div
                    className="h-3 w-3 rounded-full flex-shrink-0"
                    style={{ backgroundColor: role.color }}
                  />
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900">{role.name}</p>
                    <p className="text-sm text-gray-500 truncate">{role.description}</p>
                  </div>
                  <span className="text-sm text-gray-400">{role.userCount} users</span>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Role details / editor */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>
                {selectedRole ? (isEditing ? 'Edit Role' : 'Role Details') : 'Select a Role'}
              </CardTitle>
              {selectedRole && !isEditing && (
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm" onClick={() => setIsEditing(true)}>
                    <Edit2 className="h-4 w-4 mr-1" />
                    Edit
                  </Button>
                  {selectedRole.id > 1 && (
                    <Button variant="outline" size="sm" onClick={handleDelete} className="text-red-600 hover:text-red-700">
                      <Trash2 className="h-4 w-4 mr-1" />
                      Delete
                    </Button>
                  )}
                </div>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {selectedRole || showCreateModal ? (
              <div className="space-y-6">
                {/* Role info */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Input
                    label="Role Name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    disabled={!isEditing && !showCreateModal}
                  />
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Role Color
                    </label>
                    <div className="flex items-center gap-2">
                      <input
                        type="color"
                        value={formData.color}
                        onChange={(e) => setFormData({ ...formData, color: e.target.value })}
                        disabled={!isEditing && !showCreateModal}
                        className="h-10 w-16 rounded cursor-pointer disabled:opacity-50"
                      />
                      <span className="text-sm text-gray-500">{formData.color}</span>
                    </div>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Description
                  </label>
                  <textarea
                    rows={2}
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    disabled={!isEditing && !showCreateModal}
                    className="input"
                  />
                </div>

                {/* Permissions */}
                <div>
                  <h4 className="font-medium text-gray-900 mb-4">Permissions</h4>
                  <div className="space-y-6">
                    {permissionGroups.map((group) => {
                      const GroupIcon = group.icon
                      const groupPermissions = group.permissions.map((p) => p.key)
                      const selectedCount = groupPermissions.filter((p) =>
                        formData.permissions.includes(p)
                      ).length
                      const allSelected = selectedCount === groupPermissions.length

                      return (
                        <div key={group.name} className="border border-gray-200 rounded-lg p-4">
                          <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center gap-2">
                              <GroupIcon className="h-5 w-5 text-gray-500" />
                              <span className="font-medium text-gray-900">{group.name}</span>
                              <span className="text-sm text-gray-500">
                                ({selectedCount}/{groupPermissions.length})
                              </span>
                            </div>
                            {(isEditing || showCreateModal) && (
                              <button
                                onClick={() => handleGroupToggle(group)}
                                className="text-sm text-primary-600 hover:text-primary-700"
                              >
                                {allSelected ? 'Deselect All' : 'Select All'}
                              </button>
                            )}
                          </div>
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                            {group.permissions.map((permission) => {
                              const isSelected = formData.permissions.includes(permission.key)
                              return (
                                <label
                                  key={permission.key}
                                  className={`flex items-center gap-2 p-2 rounded-lg cursor-pointer ${
                                    isEditing || showCreateModal
                                      ? 'hover:bg-gray-50'
                                      : 'cursor-default'
                                  } ${isSelected ? 'bg-primary-50' : ''}`}
                                >
                                  <input
                                    type="checkbox"
                                    checked={isSelected}
                                    onChange={() => handlePermissionToggle(permission.key)}
                                    disabled={!isEditing && !showCreateModal}
                                    className="h-4 w-4 text-primary-600 rounded border-gray-300 focus:ring-primary-500"
                                  />
                                  <span className={`text-sm ${isSelected ? 'text-primary-700' : 'text-gray-700'}`}>
                                    {permission.label}
                                  </span>
                                </label>
                              )
                            })}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>

                {/* Actions */}
                {(isEditing || showCreateModal) && (
                  <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200">
                    <Button
                      variant="outline"
                      onClick={() => {
                        if (showCreateModal) {
                          setShowCreateModal(false)
                          resetForm()
                        } else {
                          setIsEditing(false)
                          if (selectedRole) {
                            setFormData({
                              name: selectedRole.name,
                              description: selectedRole.description,
                              color: selectedRole.color,
                              permissions: [...selectedRole.permissions],
                            })
                          }
                        }
                      }}
                    >
                      Cancel
                    </Button>
                    <Button onClick={handleSave} disabled={!formData.name}>
                      {showCreateModal ? 'Create Role' : 'Save Changes'}
                    </Button>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-12 text-gray-500">
                <Shield className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                <p>Select a role from the list to view details</p>
                <p className="text-sm mt-1">or create a new role</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default RolesPage
