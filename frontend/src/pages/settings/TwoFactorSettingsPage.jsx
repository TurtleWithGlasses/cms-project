import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Shield,
  Smartphone,
  Key,
  Copy,
  Check,
  AlertTriangle,
  RefreshCw,
  Download,
  QrCode,
  Lock,
  Unlock,
} from 'lucide-react'
import { useToast } from '../../components/ui/Toast'
import { twoFactorApi } from '../../services/api'

function TwoFactorSettingsPage() {
  const [setupStep, setSetupStep] = useState(null) // null | 'choose' | 'setup' | 'verify' | 'backup'
  const [selectedMethod, setSelectedMethod] = useState(null)
  const [setupData, setSetupData] = useState(null)
  const [verificationCode, setVerificationCode] = useState('')
  const [copiedCodes, setCopiedCodes] = useState(false)
  const [disableCode, setDisableCode] = useState('')
  const [showDisableModal, setShowDisableModal] = useState(false)

  const { toast } = useToast()
  const queryClient = useQueryClient()

  const { data: status, isLoading } = useQuery({
    queryKey: ['2fa-status'],
    queryFn: () => twoFactorApi.getStatus().then(res => res.data),
  })

  const setupMutation = useMutation({
    mutationFn: (method) => twoFactorApi.setup(method).then(res => res.data),
    onSuccess: (data) => {
      setSetupData(data)
      setSetupStep('setup')
    },
    onError: () => {
      toast({
        title: 'Setup failed',
        description: 'Failed to initialize 2FA setup. Please try again.',
        variant: 'error',
      })
    },
  })

  const verifyMutation = useMutation({
    mutationFn: (code) => twoFactorApi.verify(code),
    onSuccess: () => {
      setSetupStep('backup')
    },
    onError: () => {
      toast({
        title: 'Invalid code',
        description: 'Please check your code and try again.',
        variant: 'error',
      })
    },
  })

  const disableMutation = useMutation({
    mutationFn: (code) => twoFactorApi.disable(code),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['2fa-status'] })
      setShowDisableModal(false)
      setDisableCode('')
      toast({
        title: '2FA Disabled',
        description: 'Two-factor authentication has been disabled.',
        variant: 'success',
      })
    },
    onError: () => {
      toast({
        title: 'Invalid code',
        description: 'Please enter a valid verification code.',
        variant: 'error',
      })
    },
  })

  const regenerateMutation = useMutation({
    mutationFn: () => twoFactorApi.regenerateBackupCodes().then(res => res.data),
    onSuccess: (data) => {
      setSetupData(data)
      setSetupStep('backup')
      toast({
        title: 'Backup codes regenerated',
        description: 'Your old backup codes are no longer valid.',
        variant: 'success',
      })
    },
    onError: () => {
      toast({
        title: 'Failed to regenerate codes',
        description: 'Please try again later.',
        variant: 'error',
      })
    },
  })

  const handleCopyBackupCodes = () => {
    if (setupData?.backupCodes) {
      navigator.clipboard.writeText(setupData.backupCodes.join('\n'))
      setCopiedCodes(true)
      setTimeout(() => setCopiedCodes(false), 2000)
    }
  }

  const handleDownloadBackupCodes = () => {
    if (setupData?.backupCodes) {
      const content = `Two-Factor Authentication Backup Codes\n\nKeep these codes in a safe place. Each code can only be used once.\n\n${setupData.backupCodes.join('\n')}\n\nGenerated: ${new Date().toISOString()}`
      const blob = new Blob([content], { type: 'text/plain' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = '2fa-backup-codes.txt'
      a.click()
      URL.revokeObjectURL(url)
    }
  }

  const handleFinishSetup = () => {
    queryClient.invalidateQueries(['2fa-status'])
    setSetupStep(null)
    setSetupData(null)
    setVerificationCode('')
    toast({
      title: '2FA Enabled',
      description: 'Two-factor authentication is now active on your account.',
      variant: 'success',
    })
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  // Setup flow
  if (setupStep) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Set Up Two-Factor Authentication</h1>
          <p className="text-gray-600 mt-1">Add an extra layer of security to your account</p>
        </div>

        {/* Progress Steps */}
        <div className="flex items-center mb-8">
          {['Choose Method', 'Configure', 'Verify', 'Backup Codes'].map((step, index) => {
            const stepNum = index + 1
            const currentStep = setupStep === 'choose' ? 1 : setupStep === 'setup' ? 2 : setupStep === 'verify' ? 3 : 4
            const isActive = stepNum === currentStep
            const isCompleted = stepNum < currentStep

            return (
              <div key={step} className="flex items-center">
                <div
                  className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-medium ${
                    isCompleted
                      ? 'bg-green-500 text-white'
                      : isActive
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-200 text-gray-500'
                  }`}
                >
                  {isCompleted ? <Check className="h-4 w-4" /> : stepNum}
                </div>
                <span className={`ml-2 text-sm ${isActive ? 'text-gray-900 font-medium' : 'text-gray-500'}`}>
                  {step}
                </span>
                {index < 3 && <div className="w-12 h-px bg-gray-200 mx-4" />}
              </div>
            )
          })}
        </div>

        {/* Step Content */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          {setupStep === 'choose' && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-gray-900">Choose Your Method</h2>
              <p className="text-gray-600">Select how you want to receive verification codes</p>

              <div className="space-y-3 mt-6">
                <button
                  onClick={() => {
                    setSelectedMethod('authenticator')
                    setupMutation.mutate('authenticator')
                  }}
                  className="w-full flex items-center gap-4 p-4 border-2 border-gray-200 rounded-lg hover:border-primary-500 transition-colors text-left"
                >
                  <div className="h-12 w-12 bg-primary-100 rounded-lg flex items-center justify-center">
                    <Smartphone className="h-6 w-6 text-primary-600" />
                  </div>
                  <div>
                    <h3 className="font-medium text-gray-900">Authenticator App</h3>
                    <p className="text-sm text-gray-500">Use Google Authenticator, Authy, or similar apps</p>
                  </div>
                  <span className="ml-auto text-xs bg-green-100 text-green-700 px-2 py-1 rounded">Recommended</span>
                </button>

                <button
                  onClick={() => {
                    setSelectedMethod('sms')
                    setupMutation.mutate('sms')
                  }}
                  className="w-full flex items-center gap-4 p-4 border-2 border-gray-200 rounded-lg hover:border-primary-500 transition-colors text-left"
                >
                  <div className="h-12 w-12 bg-blue-100 rounded-lg flex items-center justify-center">
                    <Smartphone className="h-6 w-6 text-blue-600" />
                  </div>
                  <div>
                    <h3 className="font-medium text-gray-900">SMS Text Message</h3>
                    <p className="text-sm text-gray-500">Receive codes via text message</p>
                  </div>
                </button>

                <button
                  onClick={() => {
                    setSelectedMethod('email')
                    setupMutation.mutate('email')
                  }}
                  className="w-full flex items-center gap-4 p-4 border-2 border-gray-200 rounded-lg hover:border-primary-500 transition-colors text-left"
                >
                  <div className="h-12 w-12 bg-purple-100 rounded-lg flex items-center justify-center">
                    <Key className="h-6 w-6 text-purple-600" />
                  </div>
                  <div>
                    <h3 className="font-medium text-gray-900">Email</h3>
                    <p className="text-sm text-gray-500">Receive codes via email</p>
                  </div>
                </button>
              </div>

              <button
                onClick={() => setSetupStep(null)}
                className="mt-4 text-gray-600 hover:text-gray-900"
              >
                Cancel
              </button>
            </div>
          )}

          {setupStep === 'setup' && selectedMethod === 'authenticator' && setupData && (
            <div className="space-y-6">
              <h2 className="text-lg font-semibold text-gray-900">Scan QR Code</h2>
              <p className="text-gray-600">
                Scan this QR code with your authenticator app, or enter the secret key manually.
              </p>

              <div className="flex flex-col items-center py-6">
                <div className="w-48 h-48 bg-gray-100 rounded-lg flex items-center justify-center border-2 border-dashed border-gray-300">
                  <QrCode className="h-24 w-24 text-gray-400" />
                </div>
                <p className="mt-4 text-sm text-gray-500">Scan with your authenticator app</p>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm text-gray-600 mb-2">Or enter this secret key manually:</p>
                <div className="flex items-center gap-2">
                  <code className="flex-1 bg-white px-4 py-2 rounded border border-gray-200 font-mono text-sm">
                    {setupData.secret}
                  </code>
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(setupData.secret)
                      toast({ title: 'Secret key copied', variant: 'success' })
                    }}
                    className="p-2 hover:bg-gray-200 rounded-lg"
                  >
                    <Copy className="h-4 w-4" />
                  </button>
                </div>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => setSetupStep('choose')}
                  className="btn btn-secondary"
                >
                  Back
                </button>
                <button
                  onClick={() => setSetupStep('verify')}
                  className="btn btn-primary"
                >
                  Continue
                </button>
              </div>
            </div>
          )}

          {setupStep === 'verify' && (
            <div className="space-y-6">
              <h2 className="text-lg font-semibold text-gray-900">Verify Setup</h2>
              <p className="text-gray-600">
                Enter the 6-digit code from your authenticator app to confirm setup.
              </p>

              <div className="max-w-xs">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Verification Code
                </label>
                <input
                  type="text"
                  value={verificationCode}
                  onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  placeholder="000000"
                  className="input text-center text-2xl tracking-widest font-mono"
                  maxLength={6}
                />
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => setSetupStep('setup')}
                  className="btn btn-secondary"
                >
                  Back
                </button>
                <button
                  onClick={() => verifyMutation.mutate(verificationCode)}
                  disabled={verificationCode.length !== 6 || verifyMutation.isPending}
                  className="btn btn-primary"
                >
                  {verifyMutation.isPending ? 'Verifying...' : 'Verify'}
                </button>
              </div>
            </div>
          )}

          {setupStep === 'backup' && setupData?.backupCodes && (
            <div className="space-y-6">
              <div className="flex items-start gap-3">
                <AlertTriangle className="h-6 w-6 text-amber-500 flex-shrink-0 mt-0.5" />
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">Save Your Backup Codes</h2>
                  <p className="text-gray-600 mt-1">
                    Keep these codes somewhere safe. If you lose your phone, you can use these codes to access your account.
                    Each code can only be used once.
                  </p>
                </div>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <div className="grid grid-cols-2 gap-2">
                  {setupData.backupCodes.map((code, index) => (
                    <code key={index} className="bg-white px-3 py-2 rounded border border-gray-200 text-sm font-mono text-center">
                      {code}
                    </code>
                  ))}
                </div>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={handleCopyBackupCodes}
                  className="btn btn-secondary"
                >
                  {copiedCodes ? <Check className="h-4 w-4 mr-2" /> : <Copy className="h-4 w-4 mr-2" />}
                  {copiedCodes ? 'Copied!' : 'Copy Codes'}
                </button>
                <button
                  onClick={handleDownloadBackupCodes}
                  className="btn btn-secondary"
                >
                  <Download className="h-4 w-4 mr-2" />
                  Download
                </button>
              </div>

              <button
                onClick={handleFinishSetup}
                className="btn btn-primary w-full"
              >
                I've Saved My Backup Codes
              </button>
            </div>
          )}
        </div>
      </div>
    )
  }

  // Main view
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Two-Factor Authentication</h1>
        <p className="text-gray-600 mt-1">Secure your account with an additional verification step</p>
      </div>

      {/* Status Card */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex items-start gap-4">
          <div className={`h-12 w-12 rounded-full flex items-center justify-center ${
            status?.enabled ? 'bg-green-100' : 'bg-gray-100'
          }`}>
            {status?.enabled ? (
              <Lock className="h-6 w-6 text-green-600" />
            ) : (
              <Unlock className="h-6 w-6 text-gray-400" />
            )}
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-semibold text-gray-900">
                {status?.enabled ? 'Two-Factor Authentication is Enabled' : 'Two-Factor Authentication is Disabled'}
              </h2>
              <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                status?.enabled ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
              }`}>
                {status?.enabled ? 'Active' : 'Inactive'}
              </span>
            </div>
            <p className="text-gray-600 mt-1">
              {status?.enabled
                ? `Using ${status.method === 'authenticator' ? 'Authenticator App' : status.method === 'sms' ? 'SMS' : 'Email'} for verification`
                : 'Add an extra layer of security to protect your account from unauthorized access'}
            </p>
            {status?.lastUsed && (
              <p className="text-sm text-gray-500 mt-2">
                Last used: {new Date(status.lastUsed).toLocaleDateString()}
              </p>
            )}
          </div>
          {!status?.enabled ? (
            <button
              onClick={() => setSetupStep('choose')}
              className="btn btn-primary"
            >
              <Shield className="h-4 w-4 mr-2" />
              Enable 2FA
            </button>
          ) : (
            <button
              onClick={() => setShowDisableModal(true)}
              className="btn btn-secondary text-red-600 hover:text-red-700 hover:bg-red-50"
            >
              Disable 2FA
            </button>
          )}
        </div>
      </div>

      {/* Backup Codes Section */}
      {status?.enabled && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-start gap-4">
            <div className="h-12 w-12 bg-amber-100 rounded-full flex items-center justify-center">
              <Key className="h-6 w-6 text-amber-600" />
            </div>
            <div className="flex-1">
              <h2 className="text-lg font-semibold text-gray-900">Backup Codes</h2>
              <p className="text-gray-600 mt-1">
                Use these one-time codes if you lose access to your authenticator device
              </p>
              <div className="mt-3 flex items-center gap-2">
                <span className={`text-sm font-medium ${
                  status.backupCodesRemaining > 3 ? 'text-green-600' : 'text-amber-600'
                }`}>
                  {status.backupCodesRemaining} codes remaining
                </span>
                {status.backupCodesRemaining <= 3 && (
                  <AlertTriangle className="h-4 w-4 text-amber-500" />
                )}
              </div>
            </div>
            <button
              onClick={() => regenerateMutation.mutate()}
              disabled={regenerateMutation.isPending}
              className="btn btn-secondary"
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${regenerateMutation.isPending ? 'animate-spin' : ''}`} />
              Regenerate Codes
            </button>
          </div>
        </div>
      )}

      {/* Security Tips */}
      <div className="bg-blue-50 rounded-xl p-6">
        <h3 className="text-sm font-semibold text-blue-900 mb-3">Security Tips</h3>
        <ul className="space-y-2 text-sm text-blue-800">
          <li className="flex items-start gap-2">
            <Check className="h-4 w-4 text-blue-600 mt-0.5 flex-shrink-0" />
            Use an authenticator app instead of SMS when possible - it's more secure
          </li>
          <li className="flex items-start gap-2">
            <Check className="h-4 w-4 text-blue-600 mt-0.5 flex-shrink-0" />
            Store your backup codes in a secure location, like a password manager
          </li>
          <li className="flex items-start gap-2">
            <Check className="h-4 w-4 text-blue-600 mt-0.5 flex-shrink-0" />
            Never share your verification codes or backup codes with anyone
          </li>
          <li className="flex items-start gap-2">
            <Check className="h-4 w-4 text-blue-600 mt-0.5 flex-shrink-0" />
            Consider using a hardware security key for maximum protection
          </li>
        </ul>
      </div>

      {/* Disable Modal */}
      {showDisableModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4">
            <div className="fixed inset-0 bg-black/50" onClick={() => setShowDisableModal(false)} />
            <div className="relative bg-white rounded-xl shadow-xl max-w-md w-full p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Disable Two-Factor Authentication</h3>
              <p className="text-gray-600 mb-4">
                This will make your account less secure. Enter your current verification code to confirm.
              </p>
              <input
                type="text"
                value={disableCode}
                onChange={(e) => setDisableCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                placeholder="Enter 6-digit code"
                className="input mb-4"
              />
              <div className="flex gap-3">
                <button
                  onClick={() => setShowDisableModal(false)}
                  className="btn btn-secondary flex-1"
                >
                  Cancel
                </button>
                <button
                  onClick={() => disableMutation.mutate(disableCode)}
                  disabled={disableCode.length !== 6 || disableMutation.isPending}
                  className="btn bg-red-600 text-white hover:bg-red-700 flex-1"
                >
                  {disableMutation.isPending ? 'Disabling...' : 'Disable 2FA'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default TwoFactorSettingsPage
