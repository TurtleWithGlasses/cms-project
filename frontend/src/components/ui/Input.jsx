import { forwardRef } from 'react'
import { cn } from '../../utils/cn'

const Input = forwardRef(({ className, label, error, ...props }, ref) => {
  return (
    <div className="w-full">
      {label && (
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          {label}
        </label>
      )}
      <input
        ref={ref}
        className={cn(
          'block w-full rounded-lg border px-3 py-2 text-sm shadow-sm transition-colors',
          'placeholder-gray-400 dark:placeholder-gray-500',
          'bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100',
          'focus:outline-none focus:ring-1',
          error
            ? 'border-red-500 focus:border-red-500 focus:ring-red-500 dark:border-red-500'
            : 'border-gray-300 dark:border-gray-600 focus:border-primary-500 focus:ring-primary-500 dark:focus:border-primary-400',
          className
        )}
        {...props}
      />
      {error && (
        <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error}</p>
      )}
    </div>
  )
})

Input.displayName = 'Input'

export default Input
