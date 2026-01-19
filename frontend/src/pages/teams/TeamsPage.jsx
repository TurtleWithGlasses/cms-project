import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { teamsApi } from '../../services/api'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card'
import {
  Search,
  Plus,
  Edit2,
  Trash2,
  Users,
  UserPlus,
  UserMinus,
  X,
  Shield,
  Crown,
  User,
} from 'lucide-react'

function TeamsPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [showMembersModal, setShowMembersModal] = useState(false)
  const [editingTeam, setEditingTeam] = useState(null)
  const [selectedTeam, setSelectedTeam] = useState(null)
  const [formData, setFormData] = useState({
    name: '',
    description: '',
  })
  const [newMemberEmail, setNewMemberEmail] = useState('')

  // Fetch teams
  const { data: teams, isLoading } = useQuery({
    queryKey: ['teams', search],
    queryFn: () => teamsApi.getAll({ search }),
    select: (res) => res.data,
  })

  // Fetch team members when a team is selected
  const { data: teamMembers } = useQuery({
    queryKey: ['team-members', selectedTeam?.id],
    queryFn: () => teamsApi.getMembers(selectedTeam.id),
    select: (res) => res.data,
    enabled: !!selectedTeam,
  })

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data) => teamsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries(['teams'])
      closeModal()
    },
  })

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }) => teamsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['teams'])
      closeModal()
    },
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id) => teamsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries(['teams'])
    },
  })

  // Add member mutation
  const addMemberMutation = useMutation({
    mutationFn: ({ teamId, email, role }) => teamsApi.addMember(teamId, { email, role }),
    onSuccess: () => {
      queryClient.invalidateQueries(['team-members', selectedTeam?.id])
      setNewMemberEmail('')
    },
  })

  // Remove member mutation
  const removeMemberMutation = useMutation({
    mutationFn: ({ teamId, userId }) => teamsApi.removeMember(teamId, userId),
    onSuccess: () => {
      queryClient.invalidateQueries(['team-members', selectedTeam?.id])
    },
  })

  const openCreateModal = () => {
    setEditingTeam(null)
    setFormData({ name: '', description: '' })
    setShowModal(true)
  }

  const openEditModal = (team) => {
    setEditingTeam(team)
    setFormData({
      name: team.name,
      description: team.description || '',
    })
    setShowModal(true)
  }

  const openMembersModal = (team) => {
    setSelectedTeam(team)
    setShowMembersModal(true)
  }

  const closeModal = () => {
    setShowModal(false)
    setEditingTeam(null)
    setFormData({ name: '', description: '' })
  }

  const closeMembersModal = () => {
    setShowMembersModal(false)
    setSelectedTeam(null)
    setNewMemberEmail('')
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (editingTeam) {
      updateMutation.mutate({ id: editingTeam.id, data: formData })
    } else {
      createMutation.mutate(formData)
    }
  }

  const handleDelete = (team) => {
    if (window.confirm(`Delete team "${team.name}"? All members will be removed.`)) {
      deleteMutation.mutate(team.id)
    }
  }

  const handleAddMember = (e) => {
    e.preventDefault()
    if (newMemberEmail && selectedTeam) {
      addMemberMutation.mutate({
        teamId: selectedTeam.id,
        email: newMemberEmail,
        role: 'member',
      })
    }
  }

  const handleRemoveMember = (userId) => {
    if (window.confirm('Remove this member from the team?')) {
      removeMemberMutation.mutate({
        teamId: selectedTeam.id,
        userId,
      })
    }
  }

  const getRoleBadge = (role) => {
    if (role === 'owner') {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium bg-yellow-100 text-yellow-700 rounded-full">
          <Crown className="h-3 w-3" />
          Owner
        </span>
      )
    }
    if (role === 'admin') {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium bg-purple-100 text-purple-700 rounded-full">
          <Shield className="h-3 w-3" />
          Admin
        </span>
      )
    }
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium bg-gray-100 text-gray-700 rounded-full">
        <User className="h-3 w-3" />
        Member
      </span>
    )
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Teams</h1>
          <p className="text-gray-500 mt-1">Organize users into collaborative teams</p>
        </div>
        <Button onClick={openCreateModal}>
          <Plus className="h-4 w-4 mr-2" />
          Create Team
        </Button>
      </div>

      {/* Search */}
      <Card>
        <CardContent className="pt-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search teams..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input pl-10"
            />
          </div>
        </CardContent>
      </Card>

      {/* Teams grid */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>
      ) : teams?.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Users className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900">No teams</h3>
            <p className="text-gray-500 mt-1">Create your first team to collaborate with others.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {teams?.map((team) => (
            <Card key={team.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="h-12 w-12 bg-primary-100 rounded-lg flex items-center justify-center">
                      <Users className="h-6 w-6 text-primary-600" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900">{team.name}</h3>
                      <p className="text-sm text-gray-500">
                        {team.member_count || 0} members
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => openEditModal(team)}
                      className="p-2 text-gray-600 hover:text-primary-600 hover:bg-gray-100 rounded-lg"
                    >
                      <Edit2 className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(team)}
                      className="p-2 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>

                {team.description && (
                  <p className="text-sm text-gray-600 mb-4 line-clamp-2">
                    {team.description}
                  </p>
                )}

                {/* Member avatars preview */}
                <div className="flex items-center justify-between">
                  <div className="flex -space-x-2">
                    {[...Array(Math.min(team.member_count || 3, 5))].map((_, i) => (
                      <div
                        key={i}
                        className="h-8 w-8 bg-gray-200 rounded-full border-2 border-white flex items-center justify-center"
                      >
                        <User className="h-4 w-4 text-gray-500" />
                      </div>
                    ))}
                    {(team.member_count || 0) > 5 && (
                      <div className="h-8 w-8 bg-gray-100 rounded-full border-2 border-white flex items-center justify-center text-xs font-medium text-gray-600">
                        +{team.member_count - 5}
                      </div>
                    )}
                  </div>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => openMembersModal(team)}
                  >
                    <UserPlus className="h-4 w-4 mr-1" />
                    Manage
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create/Edit Team Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <h2 className="text-lg font-semibold">
                {editingTeam ? 'Edit Team' : 'Create Team'}
              </h2>
              <button
                onClick={closeModal}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <Input
                label="Team Name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
              />
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Description
                </label>
                <textarea
                  rows={3}
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="input"
                  placeholder="What does this team work on?"
                />
              </div>
              <div className="flex justify-end gap-3 pt-4">
                <Button type="button" variant="secondary" onClick={closeModal}>
                  Cancel
                </Button>
                <Button
                  type="submit"
                  isLoading={createMutation.isPending || updateMutation.isPending}
                >
                  {editingTeam ? 'Update' : 'Create'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Team Members Modal */}
      {showMembersModal && selectedTeam && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4 max-h-[80vh] flex flex-col">
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <div>
                <h2 className="text-lg font-semibold">{selectedTeam.name}</h2>
                <p className="text-sm text-gray-500">Manage team members</p>
              </div>
              <button
                onClick={closeMembersModal}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Add member form */}
            <form onSubmit={handleAddMember} className="p-4 border-b border-gray-200">
              <div className="flex gap-2">
                <Input
                  placeholder="Enter email address"
                  value={newMemberEmail}
                  onChange={(e) => setNewMemberEmail(e.target.value)}
                  className="flex-1"
                />
                <Button type="submit" isLoading={addMemberMutation.isPending}>
                  <UserPlus className="h-4 w-4 mr-1" />
                  Add
                </Button>
              </div>
            </form>

            {/* Members list */}
            <div className="flex-1 overflow-auto p-4">
              {teamMembers?.length === 0 ? (
                <div className="text-center py-8">
                  <Users className="h-10 w-10 text-gray-400 mx-auto mb-2" />
                  <p className="text-gray-500">No members yet</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {teamMembers?.map((member) => (
                    <div
                      key={member.id}
                      className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                    >
                      <div className="flex items-center gap-3">
                        <div className="h-10 w-10 bg-primary-100 rounded-full flex items-center justify-center">
                          <User className="h-5 w-5 text-primary-600" />
                        </div>
                        <div>
                          <p className="font-medium text-gray-900">
                            {member.username}
                          </p>
                          <p className="text-sm text-gray-500">{member.email}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {getRoleBadge(member.role)}
                        {member.role !== 'owner' && (
                          <button
                            onClick={() => handleRemoveMember(member.id)}
                            className="p-1.5 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded"
                          >
                            <UserMinus className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default TeamsPage
