import React, { useState } from 'react'
import { Plus, Copy, Trash2, Play } from 'lucide-react'

interface PipelineStep {
  id: string
  tool: string
  config: Record<string, unknown>
}

interface Pipeline {
  id: string
  name: string
  description: string
  steps: PipelineStep[]
  createdAt: string
}

export function Pipelines() {
  const [pipelines, setPipelines] = useState<Pipeline[]>([
    {
      id: '1',
      name: 'Deep Research Pipeline',
      description:
        'Multi-stage research with semantic search, fetch, and markdown extraction',
      steps: [
        { id: '1', tool: 'research_search', config: { provider: 'semantic' } },
        { id: '2', tool: 'research_fetch', config: { escalate: true } },
        { id: '3', tool: 'research_markdown', config: {} },
      ],
      createdAt: '2026-05-03',
    },
    {
      id: '2',
      name: 'OSINT Profiling',
      description: 'Comprehensive OSINT data collection and analysis',
      steps: [
        { id: '1', tool: 'research_github', config: {} },
        { id: '2', tool: 'threat_intel', config: {} },
        { id: '3', tool: 'passive_recon', config: {} },
      ],
      createdAt: '2026-05-02',
    },
  ])

  const [selectedPipeline, setSelectedPipeline] = useState<string | null>(null)
  const [editingPipeline, setEditingPipeline] = useState<string | null>(null)

  const currentPipeline = pipelines.find((p) => p.id === selectedPipeline)

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold text-loom-900 mb-2">Pipeline Builder</h2>
          <p className="text-gray-600">
            Compose multi-tool workflows and save them for reuse
          </p>
        </div>
        <button className="btn-primary flex items-center gap-2">
          <Plus className="w-5 h-5" />
          New Pipeline
        </button>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Pipelines List */}
        <div className="card p-6 col-span-1">
          <h3 className="text-lg font-semibold text-loom-900 mb-4">
            Saved Pipelines
          </h3>
          <div className="space-y-2">
            {pipelines.map((pipeline) => (
              <button
                key={pipeline.id}
                onClick={() => setSelectedPipeline(pipeline.id)}
                className={`w-full text-left px-4 py-3 rounded-lg transition-colors ${
                  selectedPipeline === pipeline.id
                    ? 'bg-loom-100 border border-loom-300'
                    : 'hover:bg-gray-100 border border-transparent'
                }`}
              >
                <p className="font-medium text-gray-900">{pipeline.name}</p>
                <p className="text-xs text-gray-500 mt-1">
                  {pipeline.steps.length} steps
                </p>
              </button>
            ))}
          </div>

          <div className="mt-6 pt-6 border-t border-gray-200 space-y-2">
            <p className="text-xs font-medium text-gray-600 uppercase">
              Quick Actions
            </p>
            <button className="w-full btn-secondary text-sm justify-center">
              Export All
            </button>
          </div>
        </div>

        {/* Pipeline Details */}
        <div className="card p-6 col-span-2">
          {currentPipeline ? (
            <div className="space-y-6">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-xl font-semibold text-loom-900">
                    {currentPipeline.name}
                  </h3>
                  <p className="text-gray-600 text-sm mt-1">
                    {currentPipeline.description}
                  </p>
                  <p className="text-xs text-gray-500 mt-2">
                    Created {currentPipeline.createdAt}
                  </p>
                </div>
                <div className="flex gap-2">
                  <button className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
                    <Copy className="w-5 h-5 text-gray-600" />
                  </button>
                  <button className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
                    <Trash2 className="w-5 h-5 text-red-600" />
                  </button>
                </div>
              </div>

              {/* Pipeline Steps */}
              <div className="space-y-3">
                <h4 className="font-medium text-gray-900">Pipeline Steps</h4>
                {currentPipeline.steps.map((step, index) => (
                  <div key={step.id} className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                    <div className="flex items-start gap-4">
                      <div className="flex items-center justify-center w-8 h-8 rounded-full bg-loom-600 text-white font-medium text-sm flex-shrink-0">
                        {index + 1}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-gray-900">{step.tool}</p>
                        <p className="text-xs text-gray-600 mt-1">
                          {Object.keys(step.config).length > 0
                            ? `${Object.keys(step.config).length} config options`
                            : 'Default configuration'}
                        </p>
                      </div>
                      <button className="p-2 hover:bg-gray-200 rounded transition-colors flex-shrink-0">
                        <Plus className="w-4 h-4 text-gray-600 rotate-45" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              {/* Add Step Button */}
              <button className="w-full border-2 border-dashed border-gray-300 rounded-lg py-4 text-center hover:border-loom-500 hover:bg-loom-50 transition-colors">
                <Plus className="w-5 h-5 text-gray-400 mx-auto mb-2" />
                <p className="text-sm font-medium text-gray-600">Add Step</p>
              </button>

              {/* Execute Button */}
              <button className="w-full btn-primary flex items-center justify-center gap-2">
                <Play className="w-5 h-5" />
                Execute Pipeline
              </button>
            </div>
          ) : (
            <div className="flex items-center justify-center h-96">
              <div className="text-center">
                <p className="text-gray-600 font-medium">
                  Select a pipeline to view details
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Pipeline Templates */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-loom-900 mb-4">
          Pipeline Templates
        </h3>
        <div className="grid grid-cols-2 gap-4">
          {[
            {
              name: 'Basic Research',
              description: 'Simple search and fetch workflow',
            },
            {
              name: 'OSINT Analysis',
              description: 'Multi-source intelligence gathering',
            },
            {
              name: 'Content Extraction',
              description: 'Extract and structure web content',
            },
            {
              name: 'Threat Intelligence',
              description: 'Security and threat assessment',
            },
          ].map((template) => (
            <button
              key={template.name}
              className="text-left p-4 border border-gray-300 rounded-lg hover:border-loom-500 hover:bg-loom-50 transition-colors"
            >
              <p className="font-medium text-gray-900">{template.name}</p>
              <p className="text-sm text-gray-600 mt-1">{template.description}</p>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
