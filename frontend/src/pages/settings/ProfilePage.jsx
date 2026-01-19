import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { authApi } from '../../services/api'
import useAuthStore from '../../store/authStore'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import {
  User,
  Mail,
  Lock,
  Shield,
  ShieldCheck,
  Camera,
  Save,
  Key,
} from 'lucide-react'

const profileSchema = z.object({
  username: z.string().min(3, 'Username must be at least 3 characters'),
  email: z.string().email('Invalid email address'),
})

const passwordSchema = z.object({
  currentPassword: z.string().min(1, 'Current password is required'),
  newPassword: z.string().min(8, 'Password must be at least 8 characters'),
  confirmPassword: z.string(),
}).refine((data) => data.newPassword === data.confirmPassword, {
  message: "Passwords don't match",
  path: ['confirmPassword'],
})

function ProfilePage() {
  const queryClient = useQueryClient()
  const { user, initialize } = useAuthStore()
  const [showQRCode, setShowQRCode] = useState(false)
  const [qrCodeData, setQrCodeData] = useState(null)
  const [verifyCode, setVerifyCode] = useState('')

  // Profile form
  const {
    register: registerProfile,
    handleSubmit: handleProfileSubmit,
    formState: { errors: profileErrors },
  } = useForm({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      username: user?.username || '',
      email: user?.email || '',
    },
  })

  // Password form
  const {
    register: registerPassword,
    handleSubmit: handlePasswordSubmit,
    formState: { errors: passwordErrors },
    reset: resetPassword,
  } = useForm({
    resolver: zodResolver(passwordSchema),
  })

  // Update profile mutation
  const updateProfileMutation = useMutation({
    mutationFn: (data) => authApi.updateProfile(data),
    onSuccess: () => {
      initialize()
      alert('Profile updated successfully!')
    },
  })

  // Change password mutation
  const changePasswordMutation = useMutation({
    mutationFn: (data) => authApi.changePassword(data),
    onSuccess: () => {
      resetPassword()
      alert('Password changed successfully!')
    },
  })

  // Enable 2FA mutation
  const enable2FAMutation = useMutation({
    mutationFn: () => authApi.enable2FA(),
    onSuccess: (res) => {
      setQrCodeData(res.data)
      setShowQRCode(true)
    },
  })

  // Verify 2FA mutation
  const verify2FAMutation = useMutation({
    mutationFn: (code) => authApi.verify2FASetup(code),
    onSuccess: () => {
      setShowQRCode(false)
      setQrCodeData(null)
      setVerifyCode('')
      initialize()
      alert('Two-factor authentication enabled!')
    },
  })

  // Disable 2FA mutation
  const disable2FAMutation = useMutation({
    mutationFn: () => authApi.disable2FA(),
    onSuccess: () => {
      initialize()
      alert('Two-factor authentication disabled!')
    },
  })

  const onProfileSubmit = (data) => {
    updateProfileMutation.mutate(data)
  }

  const onPasswordSubmit = (data) => {
    changePasswordMutation.mutate({
      current_password: data.currentPassword,
      new_password: data.newPassword,
    })
  }

  const handleEnable2FA = () => {
    enable2FAMutation.mutate()
  }

  const handleVerify2FA = () => {
    verify2FAMutation.mutate(verifyCode)
  }

  const handleDisable2FA = () => {
    if (window.confirm('Are you sure you want to disable two-factor authentication?')) {
      disable2FAMutation.mutate()
    }
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Profile</h1>
        <p className="text-gray-500 mt-1">Manage your account settings</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Profile card */}
        <Card className="lg:col-span-1">
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="relative inline-block">
                <div className="h-24 w-24 bg-primary-100 rounded-full flex items-center justify-center mx-auto">
                  <User className="h-12 w-12 text-primary-600" />
                </div>
                <button className="absolute bottom-0 right-0 p-2 bg-white rounded-full shadow-lg border border-gray-200 hover:bg-gray-50">
                  <Camera className="h-4 w-4 text-gray-600" />
                </button>
              </div>
              <h2 className="mt-4 text-xl font-semibold text-gray-900">
                {user?.username}
              </h2>
              <p className="text-gray-500">{user?.email}</p>
              <span className="inline-block mt-2 px-3 py-1 bg-primary-100 text-primary-700 text-sm font-medium rounded-full">
                {user?.role}
              </span>
            </div>

            <div className="mt-6 pt-6 border-t border-gray-200">
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-500">Member since</span>
                <span className="text-gray-900">
                  {user?.created_at
                    ? new Date(user.created_at).toLocaleDateString()
                    : 'N/A'}
                </span>
              </div>
              <div className="flex items-center justify-between text-sm mt-3">
                <span className="text-gray-500">Two-factor auth</span>
                <span className={user?.two_factor_enabled ? 'text-green-600' : 'text-gray-400'}>
                  {user?.two_factor_enabled ? 'Enabled' : 'Disabled'}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Settings forms */}
        <div className="lg:col-span-2 space-y-6">
          {/* Profile information */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="h-5 w-5" />
                Profile Information
              </CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleProfileSubmit(onProfileSubmit)} className="space-y-4">
                <Input
                  label="Username"
                  {...registerProfile('username')}
                  error={profileErrors.username?.message}
                />
                <Input
                  label="Email"
                  type="email"
                  {...registerProfile('email')}
                  error={profileErrors.email?.message}
                />
                <div className="flex justify-end">
                  <Button
                    type="submit"
                    isLoading={updateProfileMutation.isPending}
                  >
                    <Save className="h-4 w-4 mr-2" />
                    Save Changes
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>

          {/* Change password */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Lock className="h-5 w-5" />
                Change Password
              </CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handlePasswordSubmit(onPasswordSubmit)} className="space-y-4">
                <Input
                  label="Current Password"
                  type="password"
                  {...registerPassword('currentPassword')}
                  error={passwordErrors.currentPassword?.message}
                />
                <Input
                  label="New Password"
                  type="password"
                  {...registerPassword('newPassword')}
                  error={passwordErrors.newPassword?.message}
                />
                <Input
                  label="Confirm New Password"
                  type="password"
                  {...registerPassword('confirmPassword')}
                  error={passwordErrors.confirmPassword?.message}
                />
                <div className="flex justify-end">
                  <Button
                    type="submit"
                    isLoading={changePasswordMutation.isPending}
                  >
                    <Key className="h-4 w-4 mr-2" />
                    Change Password
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>

          {/* Two-factor authentication */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                Two-Factor Authentication
              </CardTitle>
            </CardHeader>
            <CardContent>
              {user?.two_factor_enabled ? (
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <ShieldCheck className="h-10 w-10 text-green-600" />
                    <div>
                      <p className="font-medium text-gray-900">2FA is enabled</p>
                      <p className="text-sm text-gray-500">
                        Your account is protected with two-factor authentication
                      </p>
                    </div>
                  </div>
                  <Button
                    variant="danger"
                    onClick={handleDisable2FA}
                    isLoading={disable2FAMutation.isPending}
                  >
                    Disable 2FA
                  </Button>
                </div>
              ) : showQRCode ? (
                <div className="space-y-4">
                  <div className="text-center">
                    <p className="text-sm text-gray-600 mb-4">
                      Scan this QR code with your authenticator app
                    </p>
                    {qrCodeData?.qr_code && (
                      <img
                        src={qrCodeData.qr_code}
                        alt="2FA QR Code"
                        className="mx-auto mb-4"
                      />
                    )}
                    {qrCodeData?.secret && (
                      <div className="bg-gray-100 p-3 rounded-lg">
                        <p className="text-xs text-gray-500 mb-1">Or enter this code manually:</p>
                        <code className="text-sm font-mono">{qrCodeData.secret}</code>
                      </div>
                    )}
                  </div>
                  <div>
                    <Input
                      label="Verification Code"
                      value={verifyCode}
                      onChange={(e) => setVerifyCode(e.target.value)}
                      placeholder="Enter 6-digit code"
                      maxLength={6}
                    />
                  </div>
                  <div className="flex justify-end gap-3">
                    <Button
                      variant="secondary"
                      onClick={() => {
                        setShowQRCode(false)
                        setQrCodeData(null)
                        setVerifyCode('')
                      }}
                    >
                      Cancel
                    </Button>
                    <Button
                      onClick={handleVerify2FA}
                      isLoading={verify2FAMutation.isPending}
                      disabled={verifyCode.length !== 6}
                    >
                      Verify & Enable
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Shield className="h-10 w-10 text-gray-400" />
                    <div>
                      <p className="font-medium text-gray-900">2FA is not enabled</p>
                      <p className="text-sm text-gray-500">
                        Add an extra layer of security to your account
                      </p>
                    </div>
                  </div>
                  <Button
                    onClick={handleEnable2FA}
                    isLoading={enable2FAMutation.isPending}
                  >
                    <ShieldCheck className="h-4 w-4 mr-2" />
                    Enable 2FA
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

export default ProfilePage
