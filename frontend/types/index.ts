/**
 * Shared TypeScript type definitions for Aegis frontend.
 */

// Re-export API types
export type { HealthResponse, ApiError } from '@/lib/api-client';

// Common status types
export type Status = 'idle' | 'loading' | 'success' | 'error';

// Provider types (to be expanded in Phase 2)
export type ProviderName = 'ollama' | 'openai' | 'anthropic' | 'gemini';

export interface ProviderConfig {
  name: ProviderName;
  displayName: string;
  enabled: boolean;
  models: string[];
  defaultModel: string;
}

// Project types (to be expanded in Phase 3)
export interface Project {
  id: string;
  name: string;
  description: string;
  status: 'draft' | 'active' | 'completed' | 'archived';
  createdAt: string;
  updatedAt: string;
}

// Document types (to be expanded in Phase 5)
export interface Document {
  id: string;
  projectId: string;
  title: string;
  authors: string[];
  abstract?: string;
  source: string;
  sourceId: string;
  url?: string;
  publishedDate?: string;
  createdAt: string;
}

// Job types (to be expanded in Phase 6)
export interface Job {
  id: string;
  projectId: string;
  type: 'search' | 'process' | 'analyze';
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  error?: string;
  createdAt: string;
  startedAt?: string;
  completedAt?: string;
}
