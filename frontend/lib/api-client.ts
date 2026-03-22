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
  StartResearchJobResponse,
  ProcessingStatus,
  JobStatsResponse,
  SearchResult,
  SearchFilters,
  Provider,
  ModelListResponse,
  ExportRequest,
  ExportFormat,
  CitationStyle,
  CitationResponse,
  DocumentCitationsResponse,
  AnalyticsOverview,
  PaginatedResponse,
  ProjectScope,
  ClarificationQuestion,
  SemanticSearchRequest,
  SemanticSearchResponse,
  RelatedDocument,
  DocumentChunk,
  ProgressLogList,
  JobProgressSummary,
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
    const response = await this.get<{ providers: Provider[]; default_provider: string }>('/api/v1/providers');
    return response.providers;
  }

  async getProvider(name: string): Promise<Provider> {
    return this.get<Provider>(`/api/v1/providers/${name}`);
  }

  async getProviderModels(name: string): Promise<ModelListResponse> {
    return this.get<ModelListResponse>(`/api/v1/providers/${name}/models`);
  }

  async checkProvidersHealth(): Promise<Record<string, boolean>> {
    const response = await this.get<{ providers: Record<string, boolean> }>('/api/v1/providers/health');
    return response.providers;
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
    const response = await this.get<{ projects: Project[]; total: number; page: number; page_size: number; has_more?: boolean }>(`/api/v1/projects?${params}`);
    return { items: response.projects, total: response.total, page: response.page, page_size: response.page_size, has_more: response.has_more ?? false };
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
    return this.put<Project>(`/api/v1/projects/${id}/scope`, { scope });
  }

  async updateProjectStatus(id: number, status: string): Promise<Project> {
    return this.put<Project>(`/api/v1/projects/${id}/status`, { status });
  }

  async startClarification(id: number): Promise<void> {
    return this.post<void>(`/api/v1/projects/${id}/clarify`);
  }

  // Clarification endpoints - using correct backend routes
  async getClarifications(projectId: number): Promise<ClarificationQuestion[]> {
    const response = await this.get<{ questions: ClarificationQuestion[] }>(`/api/v1/projects/${projectId}/questions`);
    return response.questions;
  }

  async generateClarifications(projectId: number): Promise<ClarificationQuestion[]> {
    const response = await this.post<{ questions: ClarificationQuestion[]; count: number }>(`/api/v1/projects/${projectId}/clarify`);
    return response.questions;
  }

  async answerClarification(projectId: number, questionId: number, answer: string): Promise<ClarificationQuestion> {
    return this.put<ClarificationQuestion>(`/api/v1/projects/${projectId}/questions/${questionId}`, { answer });
  }

  async getClarificationStatus(projectId: number): Promise<{ is_scope_complete: boolean; is_ready_for_research: boolean; unanswered_count: number }> {
    return this.get<{ is_scope_complete: boolean; is_ready_for_research: boolean; unanswered_count: number }>(`/api/v1/projects/${projectId}/clarification-status`);
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
    const response = await this.get<{ documents: Document[]; total: number; page: number; page_size: number; has_more: boolean }>(`/api/v1/documents?${params}`);
    return { items: response.documents, total: response.total, page: response.page, page_size: response.page_size, has_more: response.has_more };
  }

  async getDocument(id: number): Promise<Document> {
    return this.get<Document>(`/api/v1/documents/${id}`);
  }

  async deleteDocument(id: number): Promise<void> {
    return this.delete<void>(`/api/v1/documents/${id}`);
  }

  async processDocument(id: number): Promise<ProcessingStatus> {
    return this.post<ProcessingStatus>(`/api/v1/documents/${id}/process`);
  }

  async summarizeDocument(id: number): Promise<ProcessingStatus> {
    return this.post<ProcessingStatus>(`/api/v1/documents/${id}/summarize`);
  }

  async autoTagDocument(id: number): Promise<ProcessingStatus> {
    return this.post<ProcessingStatus>(`/api/v1/documents/${id}/auto-tag`);
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
      q: query,
      page: page.toString(),
      page_size: pageSize.toString(),
    });
    if (filters?.year_from) params.append('year_from', filters.year_from.toString());
    if (filters?.year_to) params.append('year_to', filters.year_to.toString());
    if (filters?.author) params.append('author', filters.author);
    if (filters?.open_access_only) params.append('open_access', 'true');
    if (filters?.min_citations) params.append('min_citations', filters.min_citations.toString());
    if (filters?.document_types && filters.document_types.length > 0) {
      params.append('document_types', filters.document_types.join(','));
    }
    if (sources && sources.length > 0) params.append('sources', sources.join(','));
    return this.get<SearchResult>(`/api/v1/search?${params}`);
  }

  async getSearchSources(): Promise<{ name: string; display_name: string }[]> {
    const response = await this.get<{ sources: { name: string; display_name: string }[]; total: number }>('/api/v1/search/sources');
    return response.sources;
  }

  async addPaperToProject(
    projectId: number,
    paper: { doi?: string; source?: string; primary_source?: string; source_id?: string }
  ): Promise<Document> {
    // Backend expects project_id as query param and AddPaperRequest as body
    const body = {
      doi: paper.doi,
      source_name: paper.primary_source || paper.source,
      source_id: paper.source_id,
    };
    return this.post<Document>(`/api/v1/documents/add-paper?project_id=${projectId}`, body);
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
    const response = await this.get<{ jobs: Job[]; total: number; page: number; page_size: number; has_more: boolean }>(`/api/v1/jobs?${params}`);
    return { items: response.jobs, total: response.total, page: response.page, page_size: response.page_size, has_more: response.has_more };
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

  async resumeJob(id: number): Promise<StartResearchJobResponse> {
    return this.post<StartResearchJobResponse>(`/api/v1/jobs/${id}/resume`);
  }

  async startResearchJob(projectId: number): Promise<StartResearchJobResponse> {
    return this.post<StartResearchJobResponse>('/api/v1/jobs/research', { project_id: projectId });
  }

  async getJobStats(): Promise<JobStatsResponse> {
    return this.get<JobStatsResponse>('/api/v1/jobs/stats');
  }

  // =========================================================================
  // Export Endpoints
  // =========================================================================

  async getExportFormats(): Promise<{ format: ExportFormat; name: string; description: string }[]> {
    const response = await this.get<{ formats: { id: string; name: string; content_type: string; description: string }[] }>('/api/v1/exports/formats');
    return response.formats.map(f => ({
      format: f.id as ExportFormat,
      name: f.name,
      description: f.description,
    }));
  }

  async exportDocuments(request: ExportRequest): Promise<string> {
    const response = await this.post<{ content: string; filename: string; content_type: string; document_count: number; exported_at: string }>('/api/v1/exports', request);
    return response.content;
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
    const response = await this.get<{ preview: string; total_documents: number; preview_count: number; format: string }>(`/api/v1/exports/preview?${params}`);
    return response.preview;
  }

  // =========================================================================
  // Citation Endpoints
  // =========================================================================

  async getCitationStyles(): Promise<{ style: CitationStyle; name: string }[]> {
    const response = await this.get<{ styles: { id: string; name: string; description: string; example: string }[] }>('/api/v1/citations/styles');
    return response.styles.map(s => ({
      style: s.id as CitationStyle,
      name: s.name,
    }));
  }

  async getDocumentCitations(documentId: number): Promise<DocumentCitationsResponse> {
    return this.get<DocumentCitationsResponse>(`/api/v1/citations/document/${documentId}`);
  }

  async formatCitations(documentIds: number[], style: CitationStyle): Promise<CitationResponse> {
    return this.post<CitationResponse>('/api/v1/citations/format', {
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
    // Backend returns { project_id, trends: [{year, count, ...}], from_year, to_year }
    const response = await this.get<{ trends: { year: number; count: number }[] }>(
      `/api/v1/analytics/trends?project_id=${projectId}`
    );
    // Transform to year -> count map
    const result: Record<number, number> = {};
    for (const trend of response.trends || []) {
      result[trend.year] = trend.count;
    }
    return result;
  }

  async getTopAuthors(projectId: number, limit: number = 10): Promise<{ name: string; count: number }[]> {
    // Backend returns { project_id, authors: [{name, document_count, ...}], total_unique_authors }
    const response = await this.get<{ authors: { name: string; document_count: number }[] }>(
      `/api/v1/analytics/authors?project_id=${projectId}&limit=${limit}`
    );
    // Transform to expected format
    return (response.authors || []).map(a => ({ name: a.name, count: a.document_count }));
  }

  async getKeywordAnalysis(projectId: number): Promise<{ keyword: string; count: number }[]> {
    // Backend returns { project_id, keywords: [{keyword, count, ...}], tags: [...] }
    const response = await this.get<{ keywords: { keyword: string; count: number }[] }>(
      `/api/v1/analytics/keywords?project_id=${projectId}`
    );
    // Return just the keywords array
    return response.keywords || [];
  }

  // =========================================================================
  // Semantic Search Endpoints
  // =========================================================================

  async semanticSearch(projectId: number, request: SemanticSearchRequest): Promise<SemanticSearchResponse> {
    return this.post<SemanticSearchResponse>(`/api/v1/search/semantic?project_id=${projectId}`, request);
  }

  // =========================================================================
  // Related Documents Endpoints
  // =========================================================================

  async getRelatedDocuments(documentId: number, projectId?: number, topK: number = 5): Promise<RelatedDocument[]> {
    const params = new URLSearchParams({ top_k: topK.toString() });
    if (projectId) params.append('project_id', projectId.toString());
    return this.get<RelatedDocument[]>(`/api/v1/documents/${documentId}/related?${params}`);
  }

  // =========================================================================
  // Document Chunks Endpoints
  // =========================================================================

  async getDocumentChunks(documentId: number): Promise<DocumentChunk[]> {
    return this.get<DocumentChunk[]>(`/api/v1/documents/${documentId}/chunks`);
  }

  // =========================================================================
  // Job Progress Endpoints
  // =========================================================================

  async getJobProgressLogs(
    jobId: number,
    options?: {
      entry_type?: string;
      phase?: string;
      checkpoints_only?: boolean;
      page?: number;
      page_size?: number;
    }
  ): Promise<ProgressLogList> {
    const params = new URLSearchParams();
    if (options?.entry_type) params.append('entry_type', options.entry_type);
    if (options?.phase) params.append('phase', options.phase);
    if (options?.checkpoints_only) params.append('checkpoints_only', 'true');
    params.append('page', (options?.page || 1).toString());
    params.append('page_size', (options?.page_size || 50).toString());
    return this.get<ProgressLogList>(`/api/v1/jobs/${jobId}/progress?${params}`);
  }

  async getJobProgressSummary(jobId: number): Promise<JobProgressSummary> {
    return this.get<JobProgressSummary>(`/api/v1/jobs/${jobId}/progress/summary`);
  }
}

// Export singleton instance
export const apiClient = new ApiClient();

// Export class for custom instances
export { ApiClient };
