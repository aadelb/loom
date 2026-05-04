import React from 'react'
import { AlertCircle, X } from 'lucide-react'

interface ErrorAlertProps {
  title?: string
  message: string
  onDismiss?: () => void
}

export function ErrorAlert({ title = 'Error', message, onDismiss }: ErrorAlertProps) {
  return (
    <div className="rounded-lg bg-red-50 border border-red-200 p-4 flex gap-4">
      <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
      <div className="flex-1">
        <h3 className="font-medium text-red-900">{title}</h3>
        <p className="text-sm text-red-700 mt-1">{message}</p>
      </div>
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="text-red-400 hover:text-red-600 flex-shrink-0"
        >
          <X className="w-5 h-5" />
        </button>
      )}
    </div>
  )
}
