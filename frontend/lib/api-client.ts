/**
 * Aegis API Client
 *
 * Typed client for communicating with the Aegis backend API.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  version: string;
  environment: string;
  database: 'healthy' | 'degraded' | 'unhealthy';
  redis: 'healthy' | 'degraded' | 'unhealthy';
}

export interface ApiError {
  message: string;
  detail?: string;
  status: number;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  /**
   * Make a request to the API.
   */
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;

    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error: ApiError = {
        message: 'API request failed',
        status: response.status,
      };

      try {
        const body = await response.json();
        error.detail = body.detail || body.message;
      } catch {
        error.detail = response.statusText;
      }

      throw error;
    }

    return response.json();
  }

  /**
   * GET request helper.
   */
  private get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET' });
  }

  /**
   * POST request helper.
   */
  private post<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  // =========================================================================
  // Health Endpoints
  // =========================================================================

  /**
   * Get the health status of the backend.
   */
  async health(): Promise<HealthResponse> {
    return this.get<HealthResponse>('/api/v1/health');
  }

  /**
   * Simple liveness check.
   */
  async healthLive(): Promise<{ status: string }> {
    return this.get<{ status: string }>('/api/v1/health/live');
  }

  /**
   * Readiness check.
   */
  async healthReady(): Promise<{ status: string }> {
    return this.get<{ status: string }>('/api/v1/health/ready');
  }

  // =========================================================================
  // Future endpoints will be added here as features are implemented
  // =========================================================================

  // Projects (Phase 3)
  // async createProject(data: CreateProjectRequest): Promise<Project> { ... }
  // async getProjects(): Promise<Project[]> { ... }
  // async getProject(id: string): Promise<Project> { ... }

  // Search (Phase 4)
  // async search(query: SearchQuery): Promise<SearchResults> { ... }

  // Documents (Phase 5)
  // async getDocuments(projectId: string): Promise<Document[]> { ... }

  // Jobs (Phase 6)
  // async getJobs(): Promise<Job[]> { ... }
  // async getJob(id: string): Promise<Job> { ... }
}

// Export singleton instance
export const apiClient = new ApiClient();

// Export class for custom instances
export { ApiClient };
