import axios, { AxiosInstance } from 'axios';

export interface SearchResult {
  title?: string;
  url?: string;
  snippet?: string;
  content?: string;
}

export interface HealthCheckResponse {
  status: string;
  timestamp?: string;
  version?: string;
  [key: string]: any;
}

export class LoomClient {
  private client: AxiosInstance;
  public serverUrl: string;

  constructor(serverUrl: string, apiKey?: string) {
    this.serverUrl = serverUrl;

    const headers: { [key: string]: string } = {
      'Content-Type': 'application/json',
    };

    if (apiKey) {
      headers['X-API-Key'] = apiKey;
    }

    this.client = axios.create({
      baseURL: serverUrl,
      timeout: 30000,
      headers,
    });
  }

  async search(query: string): Promise<SearchResult[]> {
    try {
      const response = await this.client.post('/api/tools/research_search', {
        query,
        num_results: 10,
      });

      // Parse response based on Loom API structure
      const results = response.data.data || response.data.results || [];

      return Array.isArray(results)
        ? results.map((result: any) => ({
            title: result.title || result.name || '',
            url: result.url || result.link || '',
            snippet: result.snippet || result.description || '',
          }))
        : [];
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(`Search failed: ${error.message}`);
      }
      throw error;
    }
  }

  async deepResearch(query: string): Promise<SearchResult[]> {
    try {
      const response = await this.client.post('/api/tools/research_deep', {
        query,
        max_depth: 3,
      });

      // Parse response based on Loom API structure
      const results = response.data.data || response.data.results || [];

      return Array.isArray(results)
        ? results.map((result: any) => ({
            title: result.title || result.name || '',
            url: result.url || result.link || '',
            snippet: result.snippet || result.description || '',
            content: result.content || result.text || '',
          }))
        : [];
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(`Deep research failed: ${error.message}`);
      }
      throw error;
    }
  }

  async reframe(text: string, strategy?: string): Promise<string> {
    try {
      const response = await this.client.post(
        '/api/tools/research_reframe',
        {
          text,
          strategy: strategy || 'general',
        }
      );

      // Parse response based on Loom API structure
      const reframed =
        response.data.data?.reframed ||
        response.data.reframed ||
        response.data;

      if (typeof reframed === 'string') {
        return reframed;
      }

      if (reframed && typeof reframed === 'object') {
        return reframed.text || reframed.output || JSON.stringify(reframed);
      }

      throw new Error('Invalid reframe response format');
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(`Reframe failed: ${error.message}`);
      }
      throw error;
    }
  }

  async checkHealth(): Promise<HealthCheckResponse> {
    try {
      const response = await this.client.get('/api/health');
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(
          `Server health check failed: ${error.message} (${this.serverUrl})`
        );
      }
      throw error;
    }
  }

  setApiKey(apiKey: string): void {
    this.client.defaults.headers.common['X-API-Key'] = apiKey;
  }

  clearApiKey(): void {
    delete this.client.defaults.headers.common['X-API-Key'];
  }
}
