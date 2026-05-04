# Loom Dashboard

A modern React dashboard for visualizing and interacting with the Loom MCP tool server. Built with TypeScript, Vite, TailwindCSS, and React Query.

## Features

- **Tool Catalog** — Browse all 738+ available tools with search and filtering
- **Analytics Dashboard** — Real-time usage metrics, latency percentiles, and error rates
- **Pipeline Builder** — Compose multi-tool workflows and execute them
- **System Health** — Monitor all subsystems with auto-refresh every 30 seconds
- **Dark/Light Mode** — Theme support (placeholder for future implementation)
- **Real-time Updates** — WebSocket support for live metrics (placeholder for future implementation)

## Quick Start

### Prerequisites

- Node.js 16+ (LTS recommended)
- npm or yarn

### Installation

```bash
cd dashboard
npm install
```

### Development

```bash
npm run dev
```

The dashboard will be available at `http://localhost:5173`

The dev server is configured to proxy API requests to `http://localhost:8787` (the Loom MCP server).

### Build

```bash
npm run build
```

Production-optimized build will be output to `dist/`.

### Preview

```bash
npm run preview
```

Serves the production build locally for testing.

## Configuration

Create a `.env` file in the dashboard root to configure API settings:

```
VITE_API_BASE_URL=http://localhost:8787
VITE_API_KEY=your-api-key-here
```

See `.env.example` for all available options.

## Project Structure

```
dashboard/
├── src/
│   ├── api/
│   │   └── client.ts           # Axios client for Loom API
│   ├── components/
│   │   ├── Layout.tsx          # Main layout with navigation
│   │   ├── LoadingSpinner.tsx  # Loading state component
│   │   └── ErrorAlert.tsx      # Error display component
│   ├── hooks/
│   │   └── useApi.ts           # React Query hooks for API calls
│   ├── pages/
│   │   ├── ToolCatalog.tsx     # Tool browser and search
│   │   ├── Analytics.tsx       # Usage metrics and charts
│   │   ├── Pipelines.tsx       # Workflow composition UI
│   │   └── Health.tsx          # System status monitoring
│   ├── App.tsx                 # Main app with routing
│   ├── main.tsx                # Entry point
│   └── index.css               # Global styles (Tailwind)
├── index.html                  # HTML template
├── vite.config.ts              # Vite configuration
├── tsconfig.json               # TypeScript configuration
├── tailwind.config.js          # TailwindCSS theme
├── postcss.config.js           # PostCSS plugins
├── package.json
└── README.md
```

## Technology Stack

- **React 18** — UI framework
- **TypeScript** — Type safety
- **Vite** — Fast build tool and dev server
- **TailwindCSS** — Utility-first CSS framework
- **React Router** — Client-side routing
- **React Query** — Server state management
- **Axios** — HTTP client
- **Recharts** — Charts and data visualization
- **Lucide React** — Icon library

## API Integration

The dashboard communicates with the Loom MCP server via HTTP:

- `/openapi.json` — Tool catalog and schema (used by Tool Catalog page)
- `/health` — Server health status
- `/health/deep` — Detailed subsystem health
- `/tools/{toolName}` — Execute individual tools
- `/tools/research_analytics_dashboard` — Analytics data

### Adding New API Calls

1. Add a method to `src/api/client.ts`
2. Create a React Query hook in `src/hooks/useApi.ts`
3. Use the hook in your component

Example:

```typescript
// client.ts
async getCustomData() {
  const response = await this.client.get('/custom/endpoint')
  return response.data
}

// useApi.ts
export function useCustomData() {
  return useQuery({
    queryKey: ['customData'],
    queryFn: () => apiClient.getCustomData(),
  })
}

// YourComponent.tsx
const { data, isLoading, error } = useCustomData()
```

## Styling

The dashboard uses TailwindCSS with a custom Loom color palette:

```javascript
colors: {
  loom: {
    50: '#f8fafc',
    100: '#f1f5f9',
    500: '#3b82f6',
    600: '#2563eb',
    700: '#1d4ed8',
    900: '#0f172a',
  }
}
```

Custom component classes are defined in `src/index.css`:
- `.card` — White card with shadow and border
- `.btn-primary` — Primary action button
- `.btn-secondary` — Secondary action button
- `.badge` — Small status badges

## Linting and Type Checking

```bash
npm run lint      # ESLint
npm run type-check # TypeScript type checking
```

## Placeholder Features

The following features are scaffolded but not yet fully implemented:

- **Tool Execution** — "Try Tool" buttons don't execute yet
- **Analytics Data** — Mock data is used; needs real API integration
- **Pipelines** — UI is ready; execution logic pending
- **Pipeline Editing** — UI is ready; state management pending
- **Dark Mode** — UI structure is ready; theme toggle pending
- **WebSocket Support** — For real-time health/analytics updates

## Performance Considerations

- **React Query** — Automatic caching, deduplication, and background refetching
- **Code Splitting** — Vite automatically chunks code by route
- **Lazy Loading** — Route components are code-split automatically
- **Stale Time** — Configured per hook (e.g., 5min for tools, 30s for health)

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

## Troubleshooting

### API Connection Fails

1. Ensure Loom server is running: `loom serve`
2. Check `VITE_API_BASE_URL` in `.env` matches your server
3. Check browser console for CORS errors
4. Verify firewall allows localhost:8787

### Tools Not Loading

1. Check `/openapi.json` endpoint is responding: `curl http://localhost:8787/openapi.json`
2. Verify tool registry has loaded: `curl http://localhost:8787/health`
3. Check React Query is fetching: Open DevTools → Network tab

### Slow Performance

1. Check network latency: React Query DevTools
2. Reduce analytics refetch interval in `src/hooks/useApi.ts`
3. Profile with React DevTools Profiler
4. Check Loom server performance

## Contributing

When adding new pages or features:

1. Create page component in `src/pages/`
2. Add route to `src/App.tsx`
3. Add navigation item to `src/components/Layout.tsx`
4. Use existing hooks and API client
5. Follow TailwindCSS + TypeScript conventions

## License

See parent Loom project LICENSE.
