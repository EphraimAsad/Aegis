'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import {
  ArrowLeft,
  FileText,
  Loader2,
  AlertCircle,
  Search,
  Filter,
  ExternalLink,
  CheckCircle,
  Clock,
  XCircle,
  Download,
  RefreshCw,
  Sparkles,
  Tag,
  MoreVertical,
  Trash2,
  Brain,
  Link2,
  Layers,
  X,
} from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import type {
  Document,
  DocumentStatus,
  Project,
  SimilarChunkResult,
  RelatedDocument,
  DocumentChunk,
} from '@/types/api';

const statusIcons: Record<DocumentStatus, typeof Clock> = {
  pending: Clock,
  downloading: Download,
  processing: Loader2,
  ready: CheckCircle,
  error: XCircle,
};

const statusColors: Record<DocumentStatus, string> = {
  pending: 'bg-gray-100 text-gray-700',
  downloading: 'bg-yellow-100 text-yellow-700',
  processing: 'bg-blue-100 text-blue-700',
  ready: 'bg-green-100 text-green-700',
  error: 'bg-red-100 text-red-700',
};

type SearchMode = 'keyword' | 'semantic';

export default function ProjectDocumentsPage() {
  const params = useParams();
  const projectId = Number(params.id);

  const [project, setProject] = useState<Project | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [processingDoc, setProcessingDoc] = useState<number | null>(null);
  const [actionMenuOpen, setActionMenuOpen] = useState<number | null>(null);

  // Advanced features state
  const [searchMode, setSearchMode] = useState<SearchMode>('keyword');
  const [semanticResults, setSemanticResults] = useState<SimilarChunkResult[]>([]);
  const [semanticLoading, setSemanticLoading] = useState(false);
  const [relatedDocsModal, setRelatedDocsModal] = useState<{ docId: number; title: string } | null>(null);
  const [relatedDocs, setRelatedDocs] = useState<RelatedDocument[]>([]);
  const [relatedLoading, setRelatedLoading] = useState(false);
  const [chunksModal, setChunksModal] = useState<{ docId: number; title: string } | null>(null);
  const [chunks, setChunks] = useState<DocumentChunk[]>([]);
  const [chunksLoading, setChunksLoading] = useState(false);

  const refreshDocuments = useCallback(async () => {
    const docsData = await apiClient.getDocuments(
      projectId,
      page,
      20,
      statusFilter === 'all' ? undefined : statusFilter
    );
    setDocuments(docsData.items);
    setTotal(docsData.total);
  }, [projectId, page, statusFilter]);

  const handleProcess = async (docId: number) => {
    setProcessingDoc(docId);
    setActionMenuOpen(null);
    try {
      await apiClient.processDocument(docId);
      await refreshDocuments();
    } catch (err) {
      console.error('Failed to process document:', err);
    } finally {
      setProcessingDoc(null);
    }
  };

  const handleSummarize = async (docId: number) => {
    setProcessingDoc(docId);
    setActionMenuOpen(null);
    try {
      await apiClient.summarizeDocument(docId);
      await refreshDocuments();
    } catch (err) {
      console.error('Failed to summarize document:', err);
    } finally {
      setProcessingDoc(null);
    }
  };

  const handleAutoTag = async (docId: number) => {
    setProcessingDoc(docId);
    setActionMenuOpen(null);
    try {
      await apiClient.autoTagDocument(docId);
      await refreshDocuments();
    } catch (err) {
      console.error('Failed to auto-tag document:', err);
    } finally {
      setProcessingDoc(null);
    }
  };

  const handleDelete = async (docId: number) => {
    if (!confirm('Are you sure you want to delete this document?')) return;
    setActionMenuOpen(null);
    try {
      await apiClient.deleteDocument(docId);
      setDocuments(documents.filter(d => d.id !== docId));
      setTotal(total - 1);
    } catch (err) {
      console.error('Failed to delete document:', err);
    }
  };

  // Semantic search handler
  const handleSemanticSearch = async () => {
    if (!searchQuery.trim()) return;
    setSemanticLoading(true);
    try {
      const response = await apiClient.semanticSearch(projectId, {
        query: searchQuery,
        top_k: 20,
        min_similarity: 0.3,
      });
      setSemanticResults(response.results);
    } catch (err) {
      console.error('Semantic search failed:', err);
      setError('Semantic search failed. Make sure documents have embeddings.');
    } finally {
      setSemanticLoading(false);
    }
  };

  // Related documents handler
  const handleViewRelated = async (docId: number, title: string) => {
    setRelatedDocsModal({ docId, title });
    setRelatedLoading(true);
    try {
      const related = await apiClient.getRelatedDocuments(docId, projectId, 10);
      setRelatedDocs(related);
    } catch (err) {
      console.error('Failed to get related documents:', err);
    } finally {
      setRelatedLoading(false);
    }
  };

  // Chunks handler
  const handleViewChunks = async (docId: number, title: string) => {
    setChunksModal({ docId, title });
    setChunksLoading(true);
    try {
      const docChunks = await apiClient.getDocumentChunks(docId);
      setChunks(docChunks);
    } catch (err) {
      console.error('Failed to get chunks:', err);
    } finally {
      setChunksLoading(false);
    }
  };

  useEffect(() => {
    async function fetchData() {
      try {
        const [projectData, docsData] = await Promise.all([
          apiClient.getProject(projectId),
          apiClient.getDocuments(
            projectId,
            page,
            20,
            statusFilter === 'all' ? undefined : statusFilter
          ),
        ]);
        setProject(projectData);
        setDocuments(docsData.items);
        setTotal(docsData.total);
      } catch (err) {
        setError('Failed to load documents');
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [projectId, page, statusFilter]);

  const filteredDocs = documents.filter((doc) => {
    if (searchMode === 'semantic' || !searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      doc.title.toLowerCase().includes(query) ||
      doc.authors?.some((a) => a.name.toLowerCase().includes(query))
    );
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error && !project) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <AlertCircle className="h-12 w-12 text-destructive" />
        <p className="text-muted-foreground">{error || 'Project not found'}</p>
        <Link
          href="/projects"
          className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm"
        >
          Back to Projects
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          href={`/projects/${projectId}`}
          className="p-2 hover:bg-muted rounded-md transition-colors"
        >
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold">Documents</h1>
          <p className="text-muted-foreground">
            {project?.name} - {total} documents
          </p>
        </div>
      </div>

      {/* Search Mode Toggle */}
      <div className="flex items-center gap-2 p-1 bg-muted rounded-lg w-fit">
        <button
          onClick={() => { setSearchMode('keyword'); setSemanticResults([]); }}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
            searchMode === 'keyword' ? 'bg-background shadow' : 'hover:bg-background/50'
          }`}
        >
          <Search className="h-4 w-4" />
          Keyword
        </button>
        <button
          onClick={() => setSearchMode('semantic')}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
            searchMode === 'semantic' ? 'bg-background shadow' : 'hover:bg-background/50'
          }`}
        >
          <Brain className="h-4 w-4" />
          Semantic
        </button>
      </div>

      {/* Search and Filters */}
      <div className="flex flex-wrap gap-4">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder={searchMode === 'semantic' ? 'Search by meaning...' : 'Search documents...'}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && searchMode === 'semantic') {
                handleSemanticSearch();
              }
            }}
            className="w-full pl-9 pr-4 py-2 border rounded-md bg-background"
          />
        </div>
        {searchMode === 'semantic' && (
          <button
            onClick={handleSemanticSearch}
            disabled={semanticLoading || !searchQuery.trim()}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md font-medium hover:bg-primary/90 disabled:opacity-50"
          >
            {semanticLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Search'}
          </button>
        )}
        {searchMode === 'keyword' && (
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-muted-foreground" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-2 border rounded-md bg-background"
            >
              <option value="all">All Status</option>
              <option value="pending">Pending</option>
              <option value="processing">Processing</option>
              <option value="ready">Ready</option>
              <option value="error">Error</option>
            </select>
          </div>
        )}
      </div>

      {/* Error Display */}
      {error && (
        <div className="p-3 bg-red-50 text-red-700 rounded-md text-sm">
          {error}
        </div>
      )}

      {/* Semantic Search Results */}
      {searchMode === 'semantic' && semanticResults.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Brain className="h-5 w-5" />
            Semantic Results ({semanticResults.length} chunks)
          </h2>
          {semanticResults.map((result) => (
            <div key={result.chunk_id} className="border rounded-lg p-4">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-medium text-sm">{result.document_title}</h3>
                    <span className="px-2 py-0.5 bg-primary/10 text-primary rounded text-xs">
                      {(result.similarity_score * 100).toFixed(1)}% match
                    </span>
                    {result.section_type && (
                      <span className="px-2 py-0.5 bg-muted rounded text-xs">
                        {result.section_type}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground line-clamp-3">
                    {result.content}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Documents List */}
      {searchMode === 'keyword' && (
        <>
          {filteredDocs.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-64 border rounded-lg bg-muted/30">
              <FileText className="h-12 w-12 text-muted-foreground mb-4" />
              <p className="text-muted-foreground">No documents found</p>
              <p className="text-sm text-muted-foreground mt-1">
                Start a research job to collect papers
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredDocs.map((doc) => {
                const StatusIcon = statusIcons[doc.status];
                return (
                  <div key={doc.id} className="border rounded-lg p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <h3 className="font-medium truncate">{doc.title}</h3>
                          {doc.doi && (
                            <a
                              href={`https://doi.org/${doc.doi}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-primary hover:underline"
                            >
                              <ExternalLink className="h-4 w-4" />
                            </a>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground mt-1">
                          {doc.authors?.slice(0, 3).map(a => typeof a === 'string' ? a : a.name).join(', ')}
                          {doc.authors && doc.authors.length > 3 && ' et al.'}
                          {doc.year && ` (${doc.year})`}
                        </p>
                        {doc.abstract && (
                          <p className="text-sm text-muted-foreground mt-2 line-clamp-2">
                            {doc.abstract}
                          </p>
                        )}
                        <div className="flex items-center gap-4 mt-3 text-xs text-muted-foreground">
                          {doc.citation_count !== undefined && (
                            <span>Citations: {doc.citation_count}</span>
                          )}
                          {doc.chunk_count !== undefined && doc.chunk_count > 0 && (
                            <span>Chunks: {doc.chunk_count}</span>
                          )}
                          {doc.is_open_access && (
                            <span className="text-green-600">Open Access</span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {/* Related Docs Button */}
                        {doc.status === 'ready' && doc.chunk_count && doc.chunk_count > 0 && (
                          <button
                            onClick={() => handleViewRelated(doc.id, doc.title)}
                            className="p-1.5 hover:bg-muted rounded transition-colors"
                            title="Find related documents"
                          >
                            <Link2 className="h-4 w-4 text-muted-foreground" />
                          </button>
                        )}
                        {/* Chunks Button */}
                        {doc.chunk_count && doc.chunk_count > 0 && (
                          <button
                            onClick={() => handleViewChunks(doc.id, doc.title)}
                            className="p-1.5 hover:bg-muted rounded transition-colors"
                            title="View document chunks"
                          >
                            <Layers className="h-4 w-4 text-muted-foreground" />
                          </button>
                        )}
                        <span
                          className={`flex items-center gap-1 px-2 py-1 rounded text-xs font-medium ${statusColors[doc.status]}`}
                        >
                          <StatusIcon className={`h-3 w-3 ${doc.status === 'processing' ? 'animate-spin' : ''}`} />
                          {doc.status}
                        </span>
                        {/* Action Menu */}
                        <div className="relative">
                          <button
                            onClick={() => setActionMenuOpen(actionMenuOpen === doc.id ? null : doc.id)}
                            disabled={processingDoc === doc.id}
                            className="p-1 hover:bg-muted rounded transition-colors disabled:opacity-50"
                          >
                            {processingDoc === doc.id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <MoreVertical className="h-4 w-4 text-muted-foreground" />
                            )}
                          </button>
                          {actionMenuOpen === doc.id && (
                            <div className="absolute right-0 top-full mt-1 w-48 bg-background border rounded-md shadow-lg z-10">
                              <button
                                onClick={() => handleProcess(doc.id)}
                                className="flex items-center gap-2 w-full px-3 py-2 text-sm hover:bg-muted text-left"
                              >
                                <RefreshCw className="h-4 w-4" />
                                Re-process
                              </button>
                              <button
                                onClick={() => handleSummarize(doc.id)}
                                className="flex items-center gap-2 w-full px-3 py-2 text-sm hover:bg-muted text-left"
                              >
                                <Sparkles className="h-4 w-4" />
                                Generate Summary
                              </button>
                              <button
                                onClick={() => handleAutoTag(doc.id)}
                                className="flex items-center gap-2 w-full px-3 py-2 text-sm hover:bg-muted text-left"
                              >
                                <Tag className="h-4 w-4" />
                                Auto-tag
                              </button>
                              <hr className="my-1" />
                              <button
                                onClick={() => handleDelete(doc.id)}
                                className="flex items-center gap-2 w-full px-3 py-2 text-sm hover:bg-muted text-left text-red-600"
                              >
                                <Trash2 className="h-4 w-4" />
                                Delete
                              </button>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                    {doc.tags && doc.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-3">
                        {doc.tags.map((tag, idx) => (
                          <span
                            key={idx}
                            className="px-2 py-0.5 bg-muted rounded text-xs"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* Pagination */}
          {total > 20 && (
            <div className="flex items-center justify-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1 border rounded-md disabled:opacity-50"
              >
                Previous
              </button>
              <span className="text-sm text-muted-foreground">
                Page {page} of {Math.ceil(total / 20)}
              </span>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={page >= Math.ceil(total / 20)}
                className="px-3 py-1 border rounded-md disabled:opacity-50"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}

      {/* Related Documents Modal */}
      {relatedDocsModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-background rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-hidden">
            <div className="flex items-center justify-between p-4 border-b">
              <div>
                <h2 className="text-lg font-semibold">Related Documents</h2>
                <p className="text-sm text-muted-foreground truncate">{relatedDocsModal.title}</p>
              </div>
              <button
                onClick={() => { setRelatedDocsModal(null); setRelatedDocs([]); }}
                className="p-1 hover:bg-muted rounded"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="p-4 overflow-auto max-h-[60vh]">
              {relatedLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin" />
                </div>
              ) : relatedDocs.length === 0 ? (
                <p className="text-center text-muted-foreground py-8">
                  No related documents found
                </p>
              ) : (
                <div className="space-y-3">
                  {relatedDocs.map((doc) => (
                    <div key={doc.document_id} className="flex items-center justify-between p-3 border rounded-lg">
                      <div className="flex-1 min-w-0 mr-4">
                        <p className="font-medium truncate">{doc.title}</p>
                      </div>
                      <span className="px-2 py-1 bg-primary/10 text-primary rounded text-sm whitespace-nowrap">
                        {(doc.similarity_score * 100).toFixed(1)}% similar
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Chunks Modal */}
      {chunksModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-background rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[80vh] overflow-hidden">
            <div className="flex items-center justify-between p-4 border-b">
              <div>
                <h2 className="text-lg font-semibold">Document Chunks</h2>
                <p className="text-sm text-muted-foreground truncate">{chunksModal.title}</p>
              </div>
              <button
                onClick={() => { setChunksModal(null); setChunks([]); }}
                className="p-1 hover:bg-muted rounded"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="p-4 overflow-auto max-h-[60vh]">
              {chunksLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin" />
                </div>
              ) : chunks.length === 0 ? (
                <p className="text-center text-muted-foreground py-8">
                  No chunks found
                </p>
              ) : (
                <div className="space-y-4">
                  {chunks.map((chunk) => (
                    <div key={chunk.id} className="border rounded-lg p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="px-2 py-0.5 bg-muted rounded text-xs font-medium">
                          Chunk {chunk.chunk_index + 1}
                        </span>
                        {chunk.section_type && (
                          <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs">
                            {chunk.section_type}
                          </span>
                        )}
                        {chunk.section_title && (
                          <span className="text-xs text-muted-foreground">
                            {chunk.section_title}
                          </span>
                        )}
                        {chunk.has_embedding && (
                          <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs">
                            Embedded
                          </span>
                        )}
                        <span className="text-xs text-muted-foreground ml-auto">
                          {chunk.token_count} tokens / {chunk.char_count} chars
                        </span>
                      </div>
                      <p className="text-sm whitespace-pre-wrap">{chunk.content}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
