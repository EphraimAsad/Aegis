/**
 * Shared TypeScript type definitions for Aegis frontend.
 */

// Re-export all API types
export * from './api';

// Common status types
export type AsyncStatus = 'idle' | 'loading' | 'success' | 'error';
