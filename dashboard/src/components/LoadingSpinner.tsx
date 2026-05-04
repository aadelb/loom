import React from 'react'

interface LoadingSpinnerProps {
  label?: string
}

export function LoadingSpinner({ label = 'Loading' }: LoadingSpinnerProps) {
  return (
    <div className="flex items-center justify-center py-12">
      <div className="text-center">
        <div className="w-12 h-12 border-4 border-loom-200 border-t-loom-600 rounded-full animate-spin mx-auto mb-4" />
        <p className="text-gray-600 font-medium">{label}...</p>
      </div>
    </div>
  )
}
