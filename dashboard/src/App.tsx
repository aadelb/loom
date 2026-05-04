import React from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClientProvider, QueryClient } from '@tanstack/react-query'
import { Layout } from './components/Layout'
import { ToolCatalog } from './pages/ToolCatalog'
import { Analytics } from './pages/Analytics'
import { Pipelines } from './pages/Pipelines'
import { Health } from './pages/Health'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    },
  },
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Layout>
          <Routes>
            <Route path="/tools" element={<ToolCatalog />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/pipelines" element={<Pipelines />} />
            <Route path="/health" element={<Health />} />
            <Route path="/" element={<Navigate to="/tools" replace />} />
          </Routes>
        </Layout>
      </Router>
    </QueryClientProvider>
  )
}

export default App
