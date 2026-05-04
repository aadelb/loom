import React, { useState, useMemo } from 'react'
import { Search, Filter } from 'lucide-react'
import { useTools } from '../hooks/useApi'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { ErrorAlert } from '../components/ErrorAlert'

interface Tool {
  name: string
  description?: string
  category?: string
  inputSchema?: {
    properties?: Record<string, unknown>
  }
}

export function ToolCatalog() {
  const { data, isLoading, error } = useTools()
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [expandedTool, setExpandedTool] = useState<string | null>(null)

  // Extract tools from OpenAPI spec (placeholder structure)
  const tools = useMemo(() => {
    if (!data || !data.tools) return []
    return Array.isArray(data.tools) ? data.tools : Object.values(data.tools || {})
  }, [data])

  // Get unique categories
  const categories = useMemo(() => {
    const cats = new Set<string>()
    tools.forEach((tool: Tool) => {
      if (tool.category) cats.add(tool.category)
    })
    return Array.from(cats).sort()
  }, [tools])

  // Filter tools
  const filteredTools = useMemo(() => {
    return tools.filter((tool: Tool) => {
      const matchesSearch =
        tool.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (tool.description || '').toLowerCase().includes(searchQuery.toLowerCase())
      const matchesCategory =
        !selectedCategory || tool.category === selectedCategory
      return matchesSearch && matchesCategory
    })
  }, [tools, searchQuery, selectedCategory])

  if (isLoading) return <LoadingSpinner label="Loading tools" />

  if (error) {
    return (
      <ErrorAlert
        title="Failed to load tools"
        message={
          error instanceof Error
            ? error.message
            : 'Unable to fetch tool catalog from server'
        }
      />
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-loom-900 mb-2">Tool Catalog</h2>
        <p className="text-gray-600">
          Browse and search all {tools.length} available tools
        </p>
      </div>

      {/* Search and Filters */}
      <div className="card p-4 space-y-4">
        <div className="relative">
          <Search className="absolute left-3 top-3 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search tools..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-loom-500"
          />
        </div>

        {/* Category Filter */}
        {categories.length > 0 && (
          <div className="flex items-center gap-2 flex-wrap">
            <Filter className="w-4 h-4 text-gray-600" />
            <button
              onClick={() => setSelectedCategory(null)}
              className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                selectedCategory === null
                  ? 'bg-loom-600 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              All
            </button>
            {categories.map((category) => (
              <button
                key={category}
                onClick={() => setSelectedCategory(category)}
                className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                  selectedCategory === category
                    ? 'bg-loom-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                {category}
              </button>
            ))}
          </div>
        )}

        <p className="text-sm text-gray-600">
          Showing {filteredTools.length} of {tools.length} tools
        </p>
      </div>

      {/* Tools Grid */}
      <div className="space-y-3">
        {filteredTools.length > 0 ? (
          filteredTools.map((tool: Tool) => (
            <div key={tool.name} className="card overflow-hidden">
              <button
                onClick={() =>
                  setExpandedTool(
                    expandedTool === tool.name ? null : tool.name
                  )
                }
                className="w-full text-left p-4 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h3 className="font-semibold text-loom-900">
                      {tool.name}
                    </h3>
                    <p className="text-sm text-gray-600 mt-1">
                      {tool.description || 'No description available'}
                    </p>
                    {tool.category && (
                      <div className="mt-2">
                        <span className="badge badge-info">
                          {tool.category}
                        </span>
                      </div>
                    )}
                  </div>
                  <div
                    className={`w-6 h-6 rounded-lg border border-gray-300 flex items-center justify-center transition-colors ${
                      expandedTool === tool.name
                        ? 'bg-loom-600 border-loom-600'
                        : ''
                    }`}
                  >
                    <span className="text-white text-sm">
                      {expandedTool === tool.name ? '−' : '+'}
                    </span>
                  </div>
                </div>
              </button>

              {/* Expanded Details */}
              {expandedTool === tool.name && (
                <div className="border-t border-gray-200 p-4 bg-gray-50">
                  <div className="space-y-4">
                    <div>
                      <h4 className="font-medium text-gray-900 mb-2">
                        Parameters
                      </h4>
                      {tool.inputSchema?.properties &&
                      Object.keys(tool.inputSchema.properties).length > 0 ? (
                        <div className="space-y-2">
                          {Object.entries(tool.inputSchema.properties).map(
                            ([key]) => (
                              <div
                                key={key}
                                className="px-3 py-2 bg-white rounded border border-gray-200 text-sm"
                              >
                                <code className="text-loom-600 font-mono">
                                  {key}
                                </code>
                              </div>
                            )
                          )}
                        </div>
                      ) : (
                        <p className="text-sm text-gray-600">
                          No parameters required
                        </p>
                      )}
                    </div>
                    <button className="btn-primary w-full">
                      Try Tool
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))
        ) : (
          <div className="card p-12 text-center">
            <p className="text-gray-600 font-medium">
              No tools found matching your search
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
