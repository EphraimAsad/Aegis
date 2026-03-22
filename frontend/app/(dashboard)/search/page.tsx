'use client';

import { useState, useEffect } from 'react';
import {
  Search,
  Loader2,
  ExternalLink,
  Plus,
  Filter,
  BookOpen,
  Calendar,
  User,
} from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import type { SearchResult, Paper, SearchFilters, Project } from '@/types/api';

const DOCUMENT_TYPES = [
  { value: 'article', label: 'Article' },
  { value: 'review', label: 'Review' },
  { value: 'preprint', label: 'Preprint' },
  { value: 'book', label: 'Book' },
  { value: 'book-chapter', label: 'Book Chapter' },
  { value: 'conference-paper', label: 'Conference Paper' },
  { value: 'thesis', label: 'Thesis' },
];

const SEARCH_SOURCES = [
  { value: 'openalex', label: 'OpenAlex' },
  { value: 'crossref', label: 'Crossref' },
  { value: 'semantic_scholar', label: 'Semantic Scholar' },
  { value: 'pubmed', label: 'PubMed' },
  { value: 'arxiv', label: 'arXiv' },
];

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState<SearchFilters>({});
  const [selectedSources, setSelectedSources] = useState<string[]>([]);
  const [addingPaper, setAddingPaper] = useState<string | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);

  useEffect(() => {
    // Fetch projects for the "Add to project" dropdown
    apiClient.getProjects(1, 100).then(data => {
      setProjects(data.items);
      if (data.items.length > 0) {
        setSelectedProjectId(data.items[0].id);
      }
    }).catch(console.error);
  }, []);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const data = await apiClient.search(
        query,
        filters,
        selectedSources.length > 0 ? selectedSources : undefined
      );
      setResults(data);
    } catch (err) {
      setError('Search failed. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const toggleSource = (source: string) => {
    setSelectedSources(prev =>
      prev.includes(source)
        ? prev.filter(s => s !== source)
        : [...prev, source]
    );
  };

  const toggleDocType = (docType: string) => {
    const current = filters.document_types || [];
    setFilters({
      ...filters,
      document_types: current.includes(docType)
        ? current.filter(d => d !== docType)
        : [...current, docType],
    });
  };

  const handleAddPaper = async (paper: Paper) => {
    if (!selectedProjectId) {
      setError('Please select a project first');
      return;
    }
    const paperId = paper.doi || paper.title;
    setAddingPaper(paperId);
    try {
      await apiClient.addPaperToProject(selectedProjectId, {
        doi: paper.doi,
        primary_source: paper.primary_source,
        source_id: paper.doi, // Use DOI as source ID fallback
      });
      // Show success feedback
    } catch (err) {
      console.error(err);
    } finally {
      setAddingPaper(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Academic Search</h1>
        <p className="text-muted-foreground">
          Search across OpenAlex, Crossref, Semantic Scholar, arXiv, and PubMed
        </p>
      </div>

      {/* Search Form */}
      <form onSubmit={handleSearch} className="space-y-4">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search for papers, topics, or keywords..."
              className="w-full pl-10 pr-4 py-2 border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
          <button
            type="button"
            onClick={() => setShowFilters(!showFilters)}
            className={`px-3 py-2 border rounded-md transition-colors ${
              showFilters ? 'bg-primary text-primary-foreground' : 'hover:bg-muted'
            }`}
          >
            <Filter className="h-4 w-4" />
          </button>
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="px-6 py-2 bg-primary text-primary-foreground rounded-md font-medium hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Search'}
          </button>
        </div>

        {/* Filters */}
        {showFilters && (
          <div className="space-y-4 p-4 border rounded-md bg-muted/30">
            {/* Basic Filters */}
            <div className="grid gap-4 sm:grid-cols-4">
              <div>
                <label className="block text-sm font-medium mb-1">Year From</label>
                <input
                  type="number"
                  value={filters.year_from || ''}
                  onChange={(e) => setFilters({ ...filters, year_from: e.target.value ? Number(e.target.value) : undefined })}
                  placeholder="2020"
                  className="w-full px-3 py-1.5 border rounded-md bg-background text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Year To</label>
                <input
                  type="number"
                  value={filters.year_to || ''}
                  onChange={(e) => setFilters({ ...filters, year_to: e.target.value ? Number(e.target.value) : undefined })}
                  placeholder="2024"
                  className="w-full px-3 py-1.5 border rounded-md bg-background text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Author</label>
                <input
                  type="text"
                  value={filters.author || ''}
                  onChange={(e) => setFilters({ ...filters, author: e.target.value || undefined })}
                  placeholder="Author name"
                  className="w-full px-3 py-1.5 border rounded-md bg-background text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Min Citations</label>
                <input
                  type="number"
                  value={filters.min_citations || ''}
                  onChange={(e) => setFilters({ ...filters, min_citations: e.target.value ? Number(e.target.value) : undefined })}
                  placeholder="0"
                  min="0"
                  className="w-full px-3 py-1.5 border rounded-md bg-background text-sm"
                />
              </div>
            </div>

            {/* Sources Selection */}
            <div>
              <label className="block text-sm font-medium mb-2">Sources</label>
              <div className="flex flex-wrap gap-2">
                {SEARCH_SOURCES.map((source) => (
                  <button
                    key={source.value}
                    type="button"
                    onClick={() => toggleSource(source.value)}
                    className={`px-3 py-1 rounded-full text-sm transition-colors ${
                      selectedSources.includes(source.value)
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-muted hover:bg-muted/80'
                    }`}
                  >
                    {source.label}
                  </button>
                ))}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                {selectedSources.length === 0 ? 'All sources selected' : `${selectedSources.length} source(s) selected`}
              </p>
            </div>

            {/* Document Types */}
            <div>
              <label className="block text-sm font-medium mb-2">Document Types</label>
              <div className="flex flex-wrap gap-2">
                {DOCUMENT_TYPES.map((docType) => (
                  <button
                    key={docType.value}
                    type="button"
                    onClick={() => toggleDocType(docType.value)}
                    className={`px-3 py-1 rounded-full text-sm transition-colors ${
                      filters.document_types?.includes(docType.value)
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-muted hover:bg-muted/80'
                    }`}
                  >
                    {docType.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Checkboxes */}
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={filters.open_access_only || false}
                  onChange={(e) => setFilters({ ...filters, open_access_only: e.target.checked || undefined })}
                  className="rounded"
                />
                Open Access Only
              </label>
            </div>

            {/* Add to Project Selection */}
            {projects.length > 0 && (
              <div>
                <label className="block text-sm font-medium mb-1">Add papers to project</label>
                <select
                  value={selectedProjectId || ''}
                  onChange={(e) => setSelectedProjectId(Number(e.target.value))}
                  className="w-full px-3 py-1.5 border rounded-md bg-background text-sm"
                >
                  {projects.map((project) => (
                    <option key={project.id} value={project.id}>
                      {project.name}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>
        )}
      </form>

      {/* Error */}
      {error && (
        <div className="p-4 bg-destructive/10 text-destructive rounded-md text-sm">
          {error}
        </div>
      )}

      {/* Results */}
      {results && (
        <div className="space-y-4">
          {/* Summary */}
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>
              Found {results.deduplicated_count} papers (from {results.original_count} across {results.sources_searched.length} sources)
            </span>
            <span>
              Sources: {results.sources_searched.join(', ')}
            </span>
          </div>

          {/* Paper List */}
          {results.papers.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-40 border rounded-lg bg-muted/30">
              <BookOpen className="h-8 w-8 text-muted-foreground mb-2" />
              <p className="text-muted-foreground">No papers found</p>
            </div>
          ) : (
            <div className="space-y-3">
              {results.papers.map((paper, index) => (
                <div key={paper.doi || index} className="border rounded-lg p-4 hover:shadow-sm transition-shadow">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold mb-1 line-clamp-2">{paper.title}</h3>
                      <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground mb-2">
                        {paper.year && (
                          <span className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            {paper.year}
                          </span>
                        )}
                        {paper.authors.length > 0 && (
                          <span className="flex items-center gap-1">
                            <User className="h-3 w-3" />
                            {paper.authors.slice(0, 3).map(a => a.name).join(', ')}
                            {paper.authors.length > 3 && ` +${paper.authors.length - 3}`}
                          </span>
                        )}
                        {paper.citation_count !== undefined && (
                          <span>{paper.citation_count} citations</span>
                        )}
                        {paper.is_open_access && (
                          <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs">
                            Open Access
                          </span>
                        )}
                        <span className="text-xs">{paper.primary_source || paper.source}</span>
                      </div>
                      {paper.abstract && (
                        <p className="text-sm text-muted-foreground line-clamp-2">
                          {paper.abstract}
                        </p>
                      )}
                    </div>
                    <div className="flex flex-col gap-2">
                      {paper.url && (
                        <a
                          href={paper.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="p-2 hover:bg-muted rounded-md transition-colors"
                          title="View paper"
                        >
                          <ExternalLink className="h-4 w-4" />
                        </a>
                      )}
                      <button
                        onClick={() => handleAddPaper(paper)}
                        disabled={addingPaper === (paper.doi || paper.title) || !selectedProjectId}
                        className="p-2 hover:bg-muted rounded-md transition-colors disabled:opacity-50"
                        title={selectedProjectId ? 'Add to project' : 'Select a project first'}
                      >
                        {addingPaper === (paper.doi || paper.title) ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Plus className="h-4 w-4" />
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Initial State */}
      {!results && !loading && (
        <div className="flex flex-col items-center justify-center h-64 border rounded-lg bg-muted/30">
          <Search className="h-12 w-12 text-muted-foreground mb-4" />
          <p className="text-muted-foreground mb-2">Enter a search query to find papers</p>
          <p className="text-sm text-muted-foreground">
            Try searching for topics like &quot;machine learning&quot;, &quot;climate change&quot;, or &quot;CRISPR&quot;
          </p>
        </div>
      )}
    </div>
  );
}
