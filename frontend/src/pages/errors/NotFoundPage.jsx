import { Link } from 'react-router-dom'
import { Home, ArrowLeft, Search } from 'lucide-react'
import Button from '../../components/ui/Button'

function NotFoundPage() {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-4">
      <div className="text-center max-w-md">
        {/* 404 illustration */}
        <div className="relative mb-8">
          <div className="text-[150px] font-bold text-gray-200 leading-none">404</div>
          <div className="absolute inset-0 flex items-center justify-center">
            <Search className="h-20 w-20 text-gray-400" />
          </div>
        </div>

        <h1 className="text-2xl font-bold text-gray-900 mb-2">Page not found</h1>
        <p className="text-gray-500 mb-8">
          Sorry, we couldn't find the page you're looking for. Perhaps you've mistyped the URL or
          the page has been moved.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link to="/dashboard">
            <Button>
              <Home className="h-4 w-4 mr-2" />
              Go to Dashboard
            </Button>
          </Link>
          <Button variant="secondary" onClick={() => window.history.back()}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Go Back
          </Button>
        </div>
      </div>
    </div>
  )
}

export default NotFoundPage
