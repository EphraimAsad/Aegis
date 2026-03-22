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

export type ProjectStatus = 'draft' | 'clarifying' | 'ready' | 'active' | 'completed' | 'archived';

export interface ProjectScope {
  keywords?: string[];
  disciplines?: string[];
  excluded_keywords?: string[];
  date_range_start?: string;  // YYYY-MM-DD format
  date_range_end?: string;    // YYYY-MM-DD format
  languages?: string[];
  document_types?: string[];
  min_citations?: number;
  include_preprints?: boolean;
  geographic_focus?: string[];
  specific_journals?: string[];
  specific_authors?: string[];
  custom_filters?: Record<string, unknown>;
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
  // Readiness fields from backend
  is_scope_complete?: boolean;
  is_ready_for_research?: boolean;
  unanswered_questions?: number;
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

export interface Journal {
  name: string;
  issn?: string;
  volume?: string;
  issue?: string;
  pages?: string;
}

export interface Document {
  id: number;
  project_id: number;
  status: DocumentStatus;
  title: string;
  abstract?: string;
  authors?: Author[];
  document_type?: string;
  year?: number;
  publication_date?: string;
  journal?: Journal;
  language?: string;
  doi?: string;
  url?: string;
  pdf_url?: string;
  open_access_url?: string;
  citation_count?: number;
  reference_count?: number;
  chunk_count?: number;
  embedding_model?: string;
  is_open_access: boolean;
  is_preprint?: boolean;
  is_retracted?: boolean;
  keywords?: string[];
  subjects?: string[];
  tags?: string[];
  summary?: string;
  key_findings?: Record<string, unknown>[];
  evidence_claims?: Record<string, unknown>[];
  source_name?: string;
  source_id?: string;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

// ============================================================================
// Job Types
// ============================================================================

export type JobStatus = 'pending' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled';
export type JobType = 'process_document' | 'embed_document' | 'summarize_document' | 'batch_process' | 'research_full' | 'search_collect' | 'analyze_collection' | 'cleanup' | 'reindex';
export type JobPriority = 'low' | 'normal' | 'high' | 'critical';

export interface Job {
  id: number;
  project_id?: number;
  job_type: JobType;
  name: string;
  description?: string;
  status: JobStatus;
  priority: JobPriority;
  progress: number;
  progress_message?: string;
  current_step: number;
  total_steps: number;
  items_processed: number;
  items_total: number;
  items_failed: number;
  result_data?: Record<string, unknown>;
  error_message?: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
}

export interface StartResearchJobResponse {
  job_id: number;
  celery_task_id: string;
  status: string;
  message: string;
}

export interface ProcessingStatus {
  document_id: number;
  status: DocumentStatus;
  message?: string;
  chunks_created?: number;
  embeddings_generated?: number;
  summary_generated?: boolean;
  tags_generated?: boolean;
}

export interface JobStatsResponse {
  total_jobs: number;
  by_status: Record<string, number>;
  by_type: Record<string, number>;
  avg_duration_seconds?: number;
  total_tokens_used: number;
  jobs_last_24h: number;
  jobs_last_7d: number;
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
  min_citations?: number;
  document_types?: string[];
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
  source?: string;  // Deprecated - use primary_source
  primary_source: string;
  sources?: string[];
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
  supports_chat: boolean;
  supports_completion: boolean;
  supports_embeddings: boolean;
  supports_streaming: boolean;
  supports_tools: boolean;
  supports_json_mode: boolean;
  supports_vision: boolean;
  max_context_length: number | null;
  max_output_tokens: number | null;
}

export interface Provider {
  name: string;
  is_default: boolean;
  is_healthy: boolean | null;
  capabilities: ProviderCapabilities;
}

export interface ModelListResponse {
  provider: string;
  models: string[];
}

// ============================================================================
// Export Types
// ============================================================================

export type ExportFormat = 'csv' | 'json' | 'markdown' | 'bibtex' | 'annotated_bibliography';
export type CitationStyle = 'apa' | 'chicago' | 'mla' | 'harvard' | 'ieee' | 'bibtex';

export interface ExportOptions {
  include_abstracts?: boolean;
  include_summaries?: boolean;
  include_key_findings?: boolean;
  include_evidence?: boolean;
  include_full_text?: boolean;
  include_metadata?: boolean;
  custom_fields?: string[];
}

export interface ExportRequest {
  project_id: number;
  document_ids?: number[];
  format: ExportFormat;
  options?: ExportOptions;
  filename?: string;
}

export interface Citation {
  document_id: number;
  title: string;
  style: CitationStyle;
  formatted: string;
  raw_components?: Record<string, unknown>;
}

export interface CitationResponse {
  citations: Citation[];
  style: CitationStyle;
  count: number;
}

export interface DocumentCitationsResponse {
  document_id: number;
  title: string;
  citations: Record<string, string>;
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
  avg_citations: number;
}

// ============================================================================
// Summary Types (for list responses)
// ============================================================================

export interface ProjectSummary {
  id: number;
  name: string;
  status: ProjectStatus;
  research_objective: string;
  created_at: string;
  updated_at: string;
  unanswered_questions: number;
}

// ============================================================================
// Clarification Types
// ============================================================================

export interface ClarificationQuestion {
  id: number;
  project_id: number;
  question: string;
  context?: string;
  is_answered: boolean;
  answer?: string;
  created_at: string;
  answered_at?: string;
}

export interface GenerateClarificationsResponse {
  questions: ClarificationQuestion[];
  count: number;
}

// ============================================================================
// Semantic Search Types
// ============================================================================

export interface SemanticSearchRequest {
  query: string;
  top_k?: number;          // default 10, max 100
  min_similarity?: number; // default 0.5, range 0.0-1.0
  document_ids?: number[];
  section_types?: string[];
}

export interface SimilarChunkResult {
  chunk_id: number;
  document_id: number;
  document_title: string;
  content: string;
  section_type?: string;
  similarity_score: number;
}

export interface SemanticSearchResponse {
  query: string;
  results: SimilarChunkResult[];
  total_results: number;
}

// ============================================================================
// Related Documents Types
// ============================================================================

export interface RelatedDocument {
  document_id: number;
  title: string;
  similarity_score: number;
}

// ============================================================================
// Document Chunks Types
// ============================================================================

export interface DocumentChunk {
  id: number;
  document_id: number;
  content: string;
  chunk_index: number;
  start_char?: number;
  end_char?: number;
  section_type?: string;
  section_title?: string;
  token_count?: number;
  char_count?: number;
  has_embedding: boolean;
  created_at: string;
}

// ============================================================================
// Job Progress Types
// ============================================================================

export type LogEntryType =
  | 'phase_start' | 'phase_complete'
  | 'paper_found' | 'paper_collected' | 'paper_processed'
  | 'insight' | 'theme' | 'checkpoint'
  | 'error' | 'recovery' | 'api_call' | 'info' | 'debug';

export interface ProgressLogEntry {
  id: number;
  job_id: number;
  entry_type: LogEntryType;
  phase?: string;
  message: string;
  data?: Record<string, unknown>;
  is_checkpoint: boolean;
  sequence: number;
  created_at: string;
}

export interface ProgressLogList {
  entries: ProgressLogEntry[];
  total: number;
  job_id: number;
}

export interface JobProgressSummary {
  job_id: number;
  total_entries: number;
  papers_found: number;
  papers_collected: number;
  papers_processed: number;
  insights_count: number;
  themes_count: number;
  errors_count: number;
  has_checkpoint: boolean;
  latest_checkpoint_at?: string;
  phases_completed: string[];
  current_phase?: string;
}
