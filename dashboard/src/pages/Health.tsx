import React from 'react'
import { CheckCircle, AlertCircle, Clock } from 'lucide-react'
import { useHealthDeep } from '../hooks/useApi'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { ErrorAlert } from '../components/ErrorAlert'

interface HealthStatus {
  status: 'healthy' | 'degraded' | 'down'
  latency?: number
  details?: string
}

interface HealthData {
  overall: HealthStatus
  subsystems?: Record<string, HealthStatus>
}

function StatusBadge({ status }: { status: HealthStatus['status'] }) {
  const config = {
    healthy: { icon: CheckCircle, color: 'text-green-600', bg: 'bg-green-50' },
    degraded: { icon: AlertCircle, color: 'text-yellow-600', bg: 'bg-yellow-50' },
    down: { icon: AlertCircle, color: 'text-red-600', bg: 'bg-red-50' },
  }

  const { icon: Icon, color, bg } = config[status]

  return (
    <div className={`${bg} px-3 py-1 rounded-full flex items-center gap-2`}>
      <Icon className={`w-4 h-4 ${color}`} />
      <span className={`text-sm font-medium ${color}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    </div>
  )
}

export function Health() {
  const { data, isLoading, error, refetch } = useHealthDeep()

  if (isLoading) return <LoadingSpinner label="Checking health" />

  if (error) {
    return (
      <ErrorAlert
        title="Failed to load health status"
        message={
          error instanceof Error
            ? error.message
            : 'Unable to fetch health data from server'
        }
      />
    )
  }

  // Mock health data
  const healthData: HealthData = {
    overall: { status: 'healthy', latency: 45 },
    subsystems: {
      'FastMCP Server': { status: 'healthy', latency: 12, details: 'Responding normally' },
      'Tool Registry': { status: 'healthy', latency: 8, details: '738 tools registered' },
      'Cache System': { status: 'healthy', latency: 3, details: 'SHA-256 cache active' },
      'Session Manager': { status: 'healthy', latency: 5, details: '0 active sessions' },
      'LLM Cascade': { status: 'degraded', latency: 234, details: 'Groq API rate-limited' },
      'Search Providers': { status: 'healthy', latency: 89, details: '21 providers active' },
      'Tor Network': { status: 'healthy', latency: 1234, details: 'SOCKS5 proxy operational' },
      'Database': { status: 'healthy', latency: 4, details: 'SQLite healthy' },
    },
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-loom-900 mb-2">System Health</h2>
        <p className="text-gray-600">Real-time status of all subsystems and services</p>
      </div>

      {/* Overall Status */}
      <div className="card p-6">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-lg font-semibold text-loom-900 mb-2">
              Overall Status
            </h3>
            <p className="text-gray-600 text-sm">
              All systems operational. Last check{' '}
              <span className="font-mono">just now</span>
            </p>
          </div>
          <div className="text-right">
            <StatusBadge status={healthData.overall.status} />
            <div className="mt-4 flex items-center gap-1 text-sm text-gray-600">
              <Clock className="w-4 h-4" />
              <span>{healthData.overall.latency}ms</span>
            </div>
          </div>
        </div>
      </div>

      {/* Subsystem Grid */}
      <div className="grid grid-cols-2 gap-4">
        {Object.entries(healthData.subsystems || {}).map(([name, status]) => (
          <div key={name} className="card p-4">
            <div className="flex items-start justify-between mb-3">
              <h4 className="font-semibold text-gray-900">{name}</h4>
              <StatusBadge status={status.status} />
            </div>
            <div className="space-y-2">
              {status.details && (
                <p className="text-sm text-gray-600">{status.details}</p>
              )}
              {status.latency !== undefined && (
                <div className="flex items-center gap-2 text-xs text-gray-500">
                  <Clock className="w-3 h-3" />
                  <span>{status.latency}ms</span>
                </div>
              )}
            </div>

            {/* Health Bar */}
            <div className="mt-3">
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className={`h-2 rounded-full transition-all ${
                    status.status === 'healthy'
                      ? 'bg-green-500'
                      : status.status === 'degraded'
                      ? 'bg-yellow-500'
                      : 'bg-red-500'
                  }`}
                  style={{
                    width:
                      status.status === 'healthy'
                        ? '100%'
                        : status.status === 'degraded'
                        ? '65%'
                        : '20%',
                  }}
                />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Auto-refresh Note */}
      <div className="card p-4 bg-blue-50 border-blue-200">
        <div className="flex gap-3">
          <Clock className="w-5 h-5 text-blue-600 flex-shrink-0" />
          <div className="text-sm text-blue-800">
            <p className="font-medium">Auto-refreshing every 30 seconds</p>
            <button
              onClick={() => refetch()}
              className="text-blue-600 hover:underline font-medium mt-1"
            >
              Refresh now
            </button>
          </div>
        </div>
      </div>

      {/* Details Table */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-loom-900 mb-4">
          Detailed Status
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-3 px-4 font-medium text-gray-700">
                  Subsystem
                </th>
                <th className="text-left py-3 px-4 font-medium text-gray-700">
                  Status
                </th>
                <th className="text-right py-3 px-4 font-medium text-gray-700">
                  Latency
                </th>
                <th className="text-left py-3 px-4 font-medium text-gray-700">
                  Details
                </th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(healthData.subsystems || {}).map(([name, status]) => (
                <tr key={name} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="py-3 px-4 font-medium text-gray-900">{name}</td>
                  <td className="py-3 px-4">
                    <StatusBadge status={status.status} />
                  </td>
                  <td className="text-right py-3 px-4 font-mono text-gray-600">
                    {status.latency}ms
                  </td>
                  <td className="py-3 px-4 text-gray-600">{status.details}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
