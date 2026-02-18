import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'
import { twoFactorApi } from '../../services/api'
import Button from '../../components/ui/Button'
import { Card, CardContent } from '../../components/ui/Card'

function TwoFactorPage() {
  const [code, setCode] = useState(['', '', '', '', '', ''])
  const [error, setError] = useState('')
  const [info, setInfo] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [emailSending, setEmailSending] = useState(false)
  const inputRefs = useRef([])
  const { verify2FA, requires2FA, tempToken } = useAuthStore()
  const navigate = useNavigate()

  useEffect(() => {
    if (!requires2FA) {
      navigate('/login')
    }
    inputRefs.current[0]?.focus()
  }, [requires2FA, navigate])

  const handleChange = (index, value) => {
    if (!/^\d*$/.test(value)) return

    const newCode = [...code]
    newCode[index] = value.slice(-1)
    setCode(newCode)

    // Auto-focus next input
    if (value && index < 5) {
      inputRefs.current[index + 1]?.focus()
    }
  }

  const handleKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !code[index] && index > 0) {
      inputRefs.current[index - 1]?.focus()
    }
  }

  const handlePaste = (e) => {
    e.preventDefault()
    const pastedData = e.clipboardData.getData('text').slice(0, 6)
    if (!/^\d+$/.test(pastedData)) return

    const newCode = [...code]
    pastedData.split('').forEach((char, i) => {
      if (i < 6) newCode[i] = char
    })
    setCode(newCode)

    if (pastedData.length === 6) {
      inputRefs.current[5]?.focus()
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)

    const fullCode = code.join('')
    if (fullCode.length !== 6) {
      setError('Please enter the complete 6-digit code')
      setIsLoading(false)
      return
    }

    try {
      await verify2FA(fullCode)
      navigate('/dashboard')
    } catch (err) {
      setError(typeof err === 'string' ? err : 'Invalid code. Please try again.')
      setCode(['', '', '', '', '', ''])
      inputRefs.current[0]?.focus()
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div>
      <div className="text-center mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Two-Factor Authentication</h1>
        <p className="text-gray-600 mt-2">
          Enter the 6-digit code from your authenticator app
        </p>
      </div>

      <Card>
        <CardContent className="pt-6">
          <form onSubmit={handleSubmit} className="space-y-6">
            {error && (
              <div className="bg-red-50 text-red-600 px-4 py-3 rounded-lg text-sm text-center">
                {error}
              </div>
            )}

            <div className="flex justify-center gap-2">
              {code.map((digit, index) => (
                <input
                  key={index}
                  ref={(el) => (inputRefs.current[index] = el)}
                  type="text"
                  inputMode="numeric"
                  maxLength={1}
                  value={digit}
                  onChange={(e) => handleChange(index, e.target.value)}
                  onKeyDown={(e) => handleKeyDown(index, e)}
                  onPaste={handlePaste}
                  className="w-12 h-14 text-center text-xl font-semibold border border-gray-300 rounded-lg focus:border-primary-500 focus:ring-1 focus:ring-primary-500 outline-none"
                />
              ))}
            </div>

            <Button type="submit" className="w-full" isLoading={isLoading}>
              Verify
            </Button>

            {info && (
              <div className="bg-blue-50 text-blue-600 px-4 py-3 rounded-lg text-sm text-center">
                {info}
              </div>
            )}

            <div className="text-center text-sm text-gray-600 space-y-2">
              <p>
                Lost access to your authenticator? You can also use a backup code.
              </p>
              {tempToken && (
                <button
                  type="button"
                  disabled={emailSending}
                  onClick={async () => {
                    setEmailSending(true)
                    setError('')
                    try {
                      const res = await twoFactorApi.sendEmailOtpForLogin(tempToken)
                      setInfo(res.data.message || 'Verification code sent to your recovery email')
                    } catch (err) {
                      setError(err.response?.data?.detail || 'Failed to send email code')
                    } finally {
                      setEmailSending(false)
                    }
                  }}
                  className="text-primary-600 hover:text-primary-700 font-medium"
                >
                  {emailSending ? 'Sending...' : 'Send code to recovery email'}
                </button>
              )}
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}

export default TwoFactorPage
