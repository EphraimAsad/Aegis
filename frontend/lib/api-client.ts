/**
 * Aegis API Client
 *
 * Typed client for communicating with the Aegis backend API.
 */

import type {
  HealthResponse,
  Project,
  CreateProjectRequest,
  UpdateProjectRequest,
  Document,
  Job,
  SearchResult,
  SearchFilters,
  Provider,
  ExportRequest,
  ExportFormat,
  CitationStyle,
  AnalyticsOverview,
  PaginatedResponse,
  ProjectScope,
} from '@/types/api';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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

  private get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET' });
  }

  private post<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  private patch<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  private put<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  private delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }

  // =========================================================================
  // Health Endpoints
  // =========================================================================

  async health(): Promise<HealthResponse> {
    return this.get<HealthResponse>('/api/v1/health');
  }

  async healthLive(): Promise<{ status: string }> {
    return this.get<{ status: string }>('/api/v1/health/live');
  }

  async healthReady(): Promise<{ status: string }> {
    return this.get<{ status: string }>('/api/v1/health/ready');
  }

  // =========================================================================
  // Provider Endpoints
  // =========================================================================

  async getProviders(): Promise<Provider[]> {
    return this.get<Provider[]>('/api/v1/providers');
  }

  async getProvider(name: string): Promise<Provider> {
    return this.get<Provider>(`/api/v1/providers/${name}`);
  }

  async getProviderModels(name: string): Promise<string[]> {
    return this.get<string[]>(`/api/v1/providers/${name}/models`);
  }

  async checkProvidersHealth(): Promise<Record<string, boolean>> {
    return this.get<Record<string, boolean>>('/api/v1/providers/health');
  }

  // =========================================================================
  // Project Endpoints
  // =========================================================================

  async getProjects(
    page: number = 1,
    pageSize: number = 20,
    status?: string
  ): Promise<PaginatedResponse<Project>> {
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString(),
    });
    if (status) params.append('status', status);
    return this.get<PaginatedResponse<Project>>(`/api/v1/projects?${params}`);
  }

  async getProject(id: number): Promise<Project> {
    return this.get<Project>(`/api/v1/projects/${id}`);
  }

  async createProject(data: CreateProjectRequest): Promise<Project> {
    return this.post<Project>('/api/v1/projects', data);
  }

  async updateProject(id: number, data: UpdateProjectRequest): Promise<Project> {
    return this.patch<Project>(`/api/v1/projects/${id}`, data);
  }

  async deleteProject(id: number): Promise<void> {
    return this.delete<void>(`/api/v1/projects/${id}`);
  }

  async updateProjectScope(id: number, scope: ProjectScope): Promise<Project> {
    return this.put<Project>(`/api/v1/projects/${id}/scope`, scope);
  }

  async updateProjectStatus(id: number, status: string): Promise<Project> {
    return this.put<Project>(`/api/v1/projects/${id}/status`, { status });
  }

  async startClarification(id: number): Promise<void> {
    return this.post<void>(`/api/v1/projects/${id}/clarify`);
  }

  // =========================================================================
  // Document Endpoints
  // =========================================================================

  async getDocuments(
    projectId: number,
    page: number = 1,
    pageSize: number = 20,
    status?: string
  ): Promise<PaginatedResponse<Document>> {
    const params = new URLSearchParams({
      project_id: projectId.toString(),
      page: page.toString(),
      page_size: pageSize.toString(),
    });
    if (status) params.append('status', status);
    return this.get<PaginatedResponse<Document>>(`/api/v1/documents?${params}`);
  }

  async getDocument(id: number): Promise<Document> {
    return this.get<Document>(`/api/v1/documents/${id}`);
  }

  async deleteDocument(id: number): Promise<void> {
    return this.delete<void>(`/api/v1/documents/${id}`);
  }

  async processDocument(id: number): Promise<Job> {
    return this.post<Job>(`/api/v1/documents/${id}/process`);
  }

  async summarizeDocument(id: number): Promise<Document> {
    return this.post<Document>(`/api/v1/documents/${id}/summarize`);
  }

  async autoTagDocument(id: number): Promise<Document> {
    return this.post<Document>(`/api/v1/documents/${id}/auto-tag`);
  }

  async getDocumentStats(projectId: number): Promise<Record<string, number>> {
    return this.get<Record<string, number>>(`/api/v1/documents/stats/${projectId}`);
  }

  // =========================================================================
  // Search Endpoints
  // =========================================================================

  async search(
    query: string,
    filters?: SearchFilters,
    sources?: string[],
    page: number = 1,
    pageSize: number = 20
  ): Promise<SearchResult> {
    const params = new URLSearchParams({
      query,
      page: page.toString(),
      page_size: pageSize.toString(),
    });
    if (filters?.year_from) params.append('year_from', filters.year_from.toString());
    if (filters?.year_to) params.append('year_to', filters.year_to.toString());
    if (filters?.author) params.append('author', filters.author);
    if (filters?.open_access_only) params.append('open_access_only', 'true');
    if (sources) sources.forEach(s => params.append('sources', s));
    return this.get<SearchResult>(`/api/v1/search?${params}`);
  }

  async getSearchSources(): Promise<{ name: string; display_name: string }[]> {
    return this.get<{ name: string; display_name: string }[]>('/api/v1/search/sources');
  }

  async addPaperToProject(projectId: number, paper: Record<string, unknown>): Promise<Document> {
    return this.post<Document>('/api/v1/documents/add-paper', {
      project_id: projectId,
      paper,
    });
  }

  // =========================================================================
  // Job Endpoints
  // =========================================================================

  async getJobs(
    projectId?: number,
    status?: string,
    page: number = 1,
    pageSize: number = 20
  ): Promise<PaginatedResponse<Job>> {
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString(),
    });
    if (projectId) params.append('project_id', projectId.toString());
    if (status) params.append('status', status);
    return this.get<PaginatedResponse<Job>>(`/api/v1/jobs?${params}`);
  }

  async getJob(id: number): Promise<Job> {
    return this.get<Job>(`/api/v1/jobs/${id}`);
  }

  async cancelJob(id: number): Promise<Job> {
    return this.post<Job>(`/api/v1/jobs/${id}/cancel`);
  }

  async retryJob(id: number): Promise<Job> {
    return this.post<Job>(`/api/v1/jobs/${id}/retry`);
  }

  async resumeJob(id: number): Promise<Job> {
    return this.post<Job>(`/api/v1/jobs/${id}/resume`);
  }

  async startResearchJob(projectId: number): Promise<Job> {
    return this.post<Job>('/api/v1/jobs/research', { project_id: projectId });
  }

  async getJobStats(): Promise<Record<string, number>> {
    return this.get<Record<string, number>>('/api/v1/jobs/stats');
  }

  // =========================================================================
  // Export Endpoints
  // =========================================================================

  async getExportFormats(): Promise<{ format: ExportFormat; name: string; description: string }[]> {
    return this.get<{ format: ExportFormat; name: string; description: string }[]>('/api/v1/exports/formats');
  }

  async exportDocuments(request: ExportRequest): Promise<string> {
    return this.post<string>('/api/v1/exports', request);
  }

  async previewExport(
    projectId: number,
    format: ExportFormat,
    documentIds?: number[]
  ): Promise<string> {
    const params = new URLSearchParams({
      project_id: projectId.toString(),
      format,
    });
    if (documentIds) documentIds.forEach(id => params.append('document_ids', id.toString()));
    return this.get<string>(`/api/v1/exports/preview?${params}`);
  }

  // =========================================================================
  // Citation Endpoints
  // =========================================================================

  async getCitationStyles(): Promise<{ style: CitationStyle; name: string }[]> {
    return this.get<{ style: CitationStyle; name: string }[]>('/api/v1/citations/styles');
  }

  async getDocumentCitations(documentId: number): Promise<Record<CitationStyle, string>> {
    return this.get<Record<CitationStyle, string>>(`/api/v1/citations/document/${documentId}`);
  }

  async formatCitations(documentIds: number[], style: CitationStyle): Promise<string[]> {
    return this.post<string[]>('/api/v1/citations/format', {
      document_ids: documentIds,
      style,
    });
  }

  // =========================================================================
  // Analytics Endpoints
  // =========================================================================

  async getAnalyticsOverview(projectId: number): Promise<AnalyticsOverview> {
    return this.get<AnalyticsOverview>(`/api/v1/analytics/overview?project_id=${projectId}`);
  }

  async getAnalyticsDashboard(projectId: number): Promise<Record<string, unknown>> {
    return this.get<Record<string, unknown>>(`/api/v1/analytics/dashboard?project_id=${projectId}`);
  }

  async getPublicationTrends(projectId: number): Promise<Record<number, number>> {
    return this.get<Record<number, number>>(`/api/v1/analytics/trends?project_id=${projectId}`);
  }

  async getTopAuthors(projectId: number, limit: number = 10): Promise<{ name: string; count: number }[]> {
    return this.get<{ name: string; count: number }[]>(
      `/api/v1/analytics/authors?project_id=${projectId}&limit=${limit}`
    );
  }

  async getKeywordAnalysis(projectId: number): Promise<{ keyword: string; count: number }[]> {
    return this.get<{ keyword: string; count: number }[]>(
      `/api/v1/analytics/keywords?project_id=${projectId}`
    );
  }
}

// Export singleton instance
export const apiClient = new ApiClient();

// Export class for custom instances
export { ApiClient };
