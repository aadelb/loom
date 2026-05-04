import React, { useState } from 'react'
import { TrendingUp, Clock, AlertCircle } from 'lucide-react'
import { useAnalytics } from '../hooks/useApi'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { ErrorAlert } from '../components/ErrorAlert'
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'

type TimeRange = '1h' | '6h' | '24h' | '7d'

export function Analytics() {
  const [timeRange, setTimeRange] = useState<TimeRange>('24h')
  const { data, isLoading, error } = useAnalytics(timeRange)

  if (isLoading) return <LoadingSpinner label="Loading analytics" />

  if (error) {
    return (
      <ErrorAlert
        title="Failed to load analytics"
        message={
          error instanceof Error
            ? error.message
            : 'Unable to fetch analytics from server'
        }
      />
    )
  }

  // Mock data structure for demonstration
  const latencyData = [
    { time: '00:00', p50: 120, p95: 450, p99: 980 },
    { time: '04:00', p50: 130, p95: 460, p99: 1000 },
    { time: '08:00', p50: 140, p95: 480, p99: 1020 },
    { time: '12:00', p50: 125, p95: 470, p99: 990 },
    { time: '16:00', p50: 135, p95: 490, p99: 1050 },
    { time: '20:00', p50: 128, p95: 455, p99: 995 },
  ]

  const topTools = [
    { name: 'research_fetch', calls: 4521, errors: 23 },
    { name: 'research_search', calls: 3890, errors: 15 },
    { name: 'research_spider', calls: 2145, errors: 8 },
    { name: 'research_markdown', calls: 1876, errors: 12 },
    { name: 'research_llm_summarize', calls: 1543, errors: 5 },
  ]

  const errorRates = [
    { tool: 'research_fetch', rate: 0.51 },
    { tool: 'research_search', rate: 0.39 },
    { tool: 'research_spider', rate: 0.37 },
    { tool: 'research_markdown', rate: 0.64 },
    { tool: 'research_llm_summarize', rate: 0.32 },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-loom-900 mb-2">Analytics</h2>
        <p className="text-gray-600">Real-time usage analytics and performance metrics</p>
      </div>

      {/* Time Range Selector */}
      <div className="flex gap-2">
        {(['1h', '6h', '24h', '7d'] as TimeRange[]).map((range) => (
          <button
            key={range}
            onClick={() => setTimeRange(range)}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              timeRange === range
                ? 'bg-loom-600 text-white'
                : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
            }`}
          >
            {range.toUpperCase()}
          </button>
        ))}
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-3 gap-4">
        <div className="card p-4">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Requests</p>
              <p className="text-3xl font-bold text-loom-900 mt-2">13,975</p>
              <p className="text-xs text-green-600 mt-2">+12% from last period</p>
            </div>
            <TrendingUp className="w-8 h-8 text-green-600 opacity-20" />
          </div>
        </div>

        <div className="card p-4">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm text-gray-600">Avg Latency</p>
              <p className="text-3xl font-bold text-loom-900 mt-2">245ms</p>
              <p className="text-xs text-green-600 mt-2">-8% improvement</p>
            </div>
            <Clock className="w-8 h-8 text-blue-600 opacity-20" />
          </div>
        </div>

        <div className="card p-4">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm text-gray-600">Error Rate</p>
              <p className="text-3xl font-bold text-loom-900 mt-2">0.43%</p>
              <p className="text-xs text-red-600 mt-2">73 errors detected</p>
            </div>
            <AlertCircle className="w-8 h-8 text-red-600 opacity-20" />
          </div>
        </div>
      </div>

      {/* Latency Chart */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-loom-900 mb-4">
          Latency Percentiles (p50, p95, p99)
        </h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={latencyData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="time" />
            <YAxis label={{ value: 'Latency (ms)', angle: -90, position: 'insideLeft' }} />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="p50" stroke="#3b82f6" dot={false} />
            <Line type="monotone" dataKey="p95" stroke="#f59e0b" dot={false} />
            <Line type="monotone" dataKey="p99" stroke="#ef4444" dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Top Tools */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-loom-900 mb-4">
          Top Tools by Request Volume
        </h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={topTools}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" angle={-45} textAnchor="end" height={80} />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="calls" fill="#3b82f6" name="Calls" />
            <Bar dataKey="errors" fill="#ef4444" name="Errors" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Error Rates Table */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-loom-900 mb-4">
          Error Rates by Tool
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-3 px-4 font-medium text-gray-700">
                  Tool
                </th>
                <th className="text-right py-3 px-4 font-medium text-gray-700">
                  Error Rate
                </th>
                <th className="text-right py-3 px-4 font-medium text-gray-700">
                  Status
                </th>
              </tr>
            </thead>
            <tbody>
              {errorRates.map((row) => (
                <tr key={row.tool} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="py-3 px-4 font-mono text-loom-600">
                    {row.tool}
                  </td>
                  <td className="text-right py-3 px-4">{(row.rate * 100).toFixed(2)}%</td>
                  <td className="text-right py-3 px-4">
                    <span
                      className={`badge ${
                        row.rate < 0.5
                          ? 'badge-success'
                          : row.rate < 1
                          ? 'badge-warning'
                          : 'badge-error'
                      }`}
                    >
                      {row.rate < 0.5 ? 'Healthy' : row.rate < 1 ? 'Warning' : 'Critical'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
