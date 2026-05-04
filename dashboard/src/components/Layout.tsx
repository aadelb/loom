import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { LayoutGrid, BarChart3, GitBranch, Activity } from 'lucide-react'
import clsx from 'clsx'

interface LayoutProps {
  children: React.ReactNode
}

const navItems = [
  { path: '/tools', label: 'Tools', icon: LayoutGrid },
  { path: '/analytics', label: 'Analytics', icon: BarChart3 },
  { path: '/pipelines', label: 'Pipelines', icon: GitBranch },
  { path: '/health', label: 'Health', icon: Activity },
]

export function Layout({ children }: LayoutProps) {
  const location = useLocation()

  return (
    <div className="min-h-screen bg-loom-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-loom-600 rounded-lg flex items-center justify-center text-white font-bold">
              L
            </div>
            <h1 className="text-xl font-bold text-loom-900">Loom Dashboard</h1>
          </div>
          <div className="text-sm text-gray-500">
            Connected to http://localhost:8787
          </div>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar Navigation */}
        <nav className="w-56 bg-white border-r border-gray-200 overflow-y-auto">
          <div className="p-4 space-y-2">
            {navItems.map(({ path, label, icon: Icon }) => {
              const isActive = location.pathname === path
              return (
                <Link
                  key={path}
                  to={path}
                  className={clsx(
                    'flex items-center gap-3 px-4 py-3 rounded-lg transition-colors font-medium text-sm',
                    isActive
                      ? 'bg-loom-100 text-loom-700'
                      : 'text-gray-700 hover:bg-gray-100'
                  )}
                >
                  <Icon className="w-5 h-5" />
                  {label}
                </Link>
              )
            })}
          </div>

          {/* Footer */}
          <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200 bg-white">
            <div className="text-xs text-gray-500">
              <p>Loom v1.0.0</p>
              <p className="text-xs mt-1">238+ tools available</p>
            </div>
          </div>
        </nav>

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
