import { useState } from 'react'
import { Link, useSearchParams, useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { authApi } from '../../services/api'
import Input from '../../components/ui/Input'
import Button from '../../components/ui/Button'
import { Lock, CheckCircle, AlertCircle, Eye, EyeOff } from 'lucide-react'

function ResetPasswordPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [success, setSuccess] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
  } = useForm()

  const password = watch('password')

  const mutation = useMutation({
    mutationFn: (data) => authApi.resetPassword(token, data.password),
    onSuccess: () => {
      setSuccess(true)
      setTimeout(() => navigate('/login'), 3000)
    },
  })

  const onSubmit = (data) => {
    mutation.mutate(data)
  }

  // Invalid or missing token
  if (!token) {
    return (
      <div className="text-center">
        <div className="mx-auto h-16 w-16 bg-red-100 rounded-full flex items-center justify-center mb-6">
          <AlertCircle className="h-8 w-8 text-red-600" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Invalid Link</h2>
        <p className="text-gray-600 mb-6">
          This password reset link is invalid or has expired.
        </p>
        <Link to="/forgot-password" className="btn btn-primary">
          Request a new link
        </Link>
      </div>
    )
  }

  // Success state
  if (success) {
    return (
      <div className="text-center">
        <div className="mx-auto h-16 w-16 bg-green-100 rounded-full flex items-center justify-center mb-6">
          <CheckCircle className="h-8 w-8 text-green-600" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Password Reset!</h2>
        <p className="text-gray-600 mb-6">
          Your password has been successfully reset.
          <br />
          Redirecting you to login...
        </p>
        <Link
          to="/login"
          className="text-primary-600 hover:text-primary-700 font-medium"
        >
          Go to login now
        </Link>
      </div>
    )
  }

  return (
    <div>
      <div className="text-center mb-8">
        <div className="mx-auto h-16 w-16 bg-primary-100 rounded-full flex items-center justify-center mb-4">
          <Lock className="h-8 w-8 text-primary-600" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900">Set new password</h2>
        <p className="text-gray-600 mt-2">
          Must be at least 8 characters with mixed case and numbers.
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div className="relative">
          <Input
            label="New Password"
            type={showPassword ? 'text' : 'password'}
            placeholder="Enter new password"
            error={errors.password?.message}
            {...register('password', {
              required: 'Password is required',
              minLength: {
                value: 8,
                message: 'Password must be at least 8 characters',
              },
              pattern: {
                value: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/,
                message: 'Password must contain uppercase, lowercase, and number',
              },
            })}
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-3 top-9 text-gray-400 hover:text-gray-600"
          >
            {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>

        <div className="relative">
          <Input
            label="Confirm Password"
            type={showConfirmPassword ? 'text' : 'password'}
            placeholder="Confirm new password"
            error={errors.confirmPassword?.message}
            {...register('confirmPassword', {
              required: 'Please confirm your password',
              validate: (value) =>
                value === password || 'Passwords do not match',
            })}
          />
          <button
            type="button"
            onClick={() => setShowConfirmPassword(!showConfirmPassword)}
            className="absolute right-3 top-9 text-gray-400 hover:text-gray-600"
          >
            {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>

        {/* Password strength indicator */}
        <div className="space-y-2">
          <div className="flex gap-1">
            {[1, 2, 3, 4].map((level) => {
              const strength = getPasswordStrength(password)
              return (
                <div
                  key={level}
                  className={`h-1 flex-1 rounded ${
                    level <= strength
                      ? strength <= 1 ? 'bg-red-500' :
                        strength === 2 ? 'bg-yellow-500' :
                        strength === 3 ? 'bg-blue-500' : 'bg-green-500'
                      : 'bg-gray-200'
                  }`}
                />
              )
            })}
          </div>
          <p className="text-xs text-gray-500">
            {password ? getPasswordStrengthText(password) : 'Enter a password'}
          </p>
        </div>

        {mutation.isError && (
          <div className="p-3 rounded-lg bg-red-50 text-red-600 text-sm">
            {mutation.error?.response?.data?.message ||
              'Failed to reset password. The link may have expired.'}
          </div>
        )}

        <Button
          type="submit"
          className="w-full"
          disabled={mutation.isPending}
        >
          {mutation.isPending ? 'Resetting...' : 'Reset password'}
        </Button>
      </form>
    </div>
  )
}

function getPasswordStrength(password) {
  if (!password) return 0
  let strength = 0
  if (password.length >= 8) strength++
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength++
  if (/\d/.test(password)) strength++
  if (/[^a-zA-Z0-9]/.test(password)) strength++
  return strength
}

function getPasswordStrengthText(password) {
  const strength = getPasswordStrength(password)
  const texts = ['Very weak', 'Weak', 'Fair', 'Good', 'Strong']
  return texts[strength]
}

export default ResetPasswordPage
