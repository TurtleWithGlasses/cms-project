import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { authApi } from '../../services/api'
import Input from '../../components/ui/Input'
import Button from '../../components/ui/Button'
import { Mail, ArrowLeft, CheckCircle } from 'lucide-react'

function ForgotPasswordPage() {
  const [submitted, setSubmitted] = useState(false)
  const {
    register,
    handleSubmit,
    formState: { errors },
    getValues,
  } = useForm()

  const mutation = useMutation({
    mutationFn: (data) => authApi.forgotPassword(data.email),
    onSuccess: () => setSubmitted(true),
  })

  const onSubmit = (data) => {
    mutation.mutate(data)
  }

  if (submitted) {
    return (
      <div className="text-center">
        <div className="mx-auto h-16 w-16 bg-green-100 rounded-full flex items-center justify-center mb-6">
          <CheckCircle className="h-8 w-8 text-green-600" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Check your email</h2>
        <p className="text-gray-600 mb-6">
          We've sent a password reset link to{' '}
          <span className="font-medium">{getValues('email')}</span>
        </p>
        <p className="text-sm text-gray-500 mb-6">
          Didn't receive the email? Check your spam folder or{' '}
          <button
            onClick={() => mutation.mutate({ email: getValues('email') })}
            className="text-primary-600 hover:text-primary-700 font-medium"
          >
            click to resend
          </button>
        </p>
        <Link
          to="/login"
          className="inline-flex items-center text-sm font-medium text-primary-600 hover:text-primary-700"
        >
          <ArrowLeft className="h-4 w-4 mr-1" />
          Back to login
        </Link>
      </div>
    )
  }

  return (
    <div>
      <div className="text-center mb-8">
        <div className="mx-auto h-16 w-16 bg-primary-100 rounded-full flex items-center justify-center mb-4">
          <Mail className="h-8 w-8 text-primary-600" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900">Forgot password?</h2>
        <p className="text-gray-600 mt-2">
          No worries, we'll send you reset instructions.
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <Input
          label="Email"
          type="email"
          placeholder="Enter your email"
          error={errors.email?.message}
          {...register('email', {
            required: 'Email is required',
            pattern: {
              value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
              message: 'Invalid email address',
            },
          })}
        />

        {mutation.isError && (
          <div className="p-3 rounded-lg bg-red-50 text-red-600 text-sm">
            {mutation.error?.response?.data?.message || 'An error occurred. Please try again.'}
          </div>
        )}

        <Button
          type="submit"
          className="w-full"
          disabled={mutation.isPending}
        >
          {mutation.isPending ? 'Sending...' : 'Reset password'}
        </Button>
      </form>

      <div className="mt-6 text-center">
        <Link
          to="/login"
          className="inline-flex items-center text-sm font-medium text-gray-600 hover:text-gray-900"
        >
          <ArrowLeft className="h-4 w-4 mr-1" />
          Back to login
        </Link>
      </div>
    </div>
  )
}

export default ForgotPasswordPage
