/**
 * API Types for Aegis Frontend
 *
 * These types match the backend Pydantic schemas.
 */

// ============================================================================
// Common Types
// ============================================================================

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

// ============================================================================
// Health Types
// ============================================================================

export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  version: string;
  environment: string;
  database: 'healthy' | 'degraded' | 'unhealthy';
  redis: 'healthy' | 'degraded' | 'unhealthy';
}

// ============================================================================
// Project Types
// ============================================================================

export type ProjectStatus = 'draft' | 'clarifying' | 'ready' | 'searching' | 'processing' | 'complete' | 'archived';

export interface ProjectScope {
  keywords?: string[];
  disciplines?: string[];
  year_from?: number;
  year_to?: number;
  document_types?: string[];
  sources?: string[];
  exclusions?: string[];
}

export interface Project {
  id: number;
  name: string;
  description?: string;
  research_objective: string;
  status: ProjectStatus;
  scope?: ProjectScope;
  provider?: string;
  model?: string;
  max_results_per_source: number;
  sources_enabled: string[];
  created_at: string;
  updated_at: string;
}

export interface CreateProjectRequest {
  name: string;
  description?: string;
  research_objective: string;
  provider?: string;
  model?: string;
  max_results_per_source?: number;
  sources_enabled?: string[];
}

export interface UpdateProjectRequest {
  name?: string;
  description?: string;
  research_objective?: string;
  provider?: string;
  model?: string;
  max_results_per_source?: number;
  sources_enabled?: string[];
}

// ============================================================================
// Document Types
// ============================================================================

export type DocumentStatus = 'pending' | 'downloading' | 'processing' | 'ready' | 'error';

export interface Author {
  name: string;
  orcid?: string;
  affiliations?: string[];
}

export interface Document {
  id: number;
  project_id: number;
  status: DocumentStatus;
  title: string;
  abstract?: string;
  authors?: Author[];
  year?: number;
  doi?: string;
  url?: string;
  pdf_url?: string;
  citation_count?: number;
  is_open_access: boolean;
  tags?: string[];
  summary?: string;
  created_at: string;
  updated_at: string;
}

// ============================================================================
// Job Types
// ============================================================================

export type JobStatus = 'pending' | 'queued' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled';
export type JobType = 'research' | 'process_document' | 'batch_process' | 'chunk' | 'embed' | 'summarize';
export type JobPriority = 'low' | 'normal' | 'high' | 'critical';

export interface Job {
  id: number;
  project_id: number;
  job_type: JobType;
  status: JobStatus;
  priority: JobPriority;
  progress: number;
  total_steps?: number;
  current_step?: number;
  message?: string;
  result?: Record<string, unknown>;
  error_message?: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
  updated_at: string;
}

// ============================================================================
// Search Types
// ============================================================================

export interface SearchFilters {
  year_from?: number;
  year_to?: number;
  author?: string;
  title_contains?: string;
  open_access_only?: boolean;
}

export interface Paper {
  title: string;
  abstract?: string;
  authors: Author[];
  year?: number;
  doi?: string;
  url?: string;
  pdf_url?: string;
  citation_count?: number;
  is_open_access: boolean;
  source: string;
}

export interface SearchResult {
  papers: Paper[];
  total_from_sources: Record<string, number>;
  deduplicated_count: number;
  original_count: number;
  query: string;
  sources_searched: string[];
  errors: Record<string, string>;
}

// ============================================================================
// Provider Types
// ============================================================================

export interface ProviderCapabilities {
  chat: boolean;
  completion: boolean;
  embeddings: boolean;
  streaming: boolean;
}

export interface Provider {
  name: string;
  display_name: string;
  is_available: boolean;
  is_default: boolean;
  capabilities: ProviderCapabilities;
  default_model?: string;
  available_models: string[];
}

// ============================================================================
// Export Types
// ============================================================================

export type ExportFormat = 'csv' | 'json' | 'markdown' | 'bibtex' | 'annotated';
export type CitationStyle = 'apa' | 'chicago' | 'mla' | 'harvard' | 'ieee' | 'bibtex';

export interface ExportRequest {
  project_id: number;
  document_ids?: number[];
  format: ExportFormat;
  include_abstract?: boolean;
  include_summary?: boolean;
}

// ============================================================================
// Analytics Types
// ============================================================================

export interface AnalyticsOverview {
  project_id: number;
  total_documents: number;
  documents_by_status: Record<DocumentStatus, number>;
  documents_by_year: Record<number, number>;
  total_citations: number;
  open_access_count: number;
  average_citations: number;
}
