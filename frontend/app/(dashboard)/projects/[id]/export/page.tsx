'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import {
  ArrowLeft,
  Download,
  Loader2,
  AlertCircle,
  FileJson,
  FileText,
  FileSpreadsheet,
  BookOpen,
  Copy,
  Check,
} from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import type { Project, ExportFormat, CitationStyle } from '@/types/api';

const formatIcons: Record<ExportFormat, typeof FileText> = {
  csv: FileSpreadsheet,
  json: FileJson,
  markdown: FileText,
  bibtex: BookOpen,
  annotated: FileText,
};

const formatDescriptions: Record<ExportFormat, string> = {
  csv: 'Spreadsheet format for Excel, Google Sheets',
  json: 'Structured data format for programming',
  markdown: 'Formatted text with summaries and notes',
  bibtex: 'Bibliography format for LaTeX documents',
  annotated: 'Markdown with annotations and evidence',
};

const citationStyleNames: Record<CitationStyle, string> = {
  apa: 'APA (7th Edition)',
  chicago: 'Chicago',
  mla: 'MLA',
  harvard: 'Harvard',
  ieee: 'IEEE',
  bibtex: 'BibTeX',
};

export default function ProjectExportPage() {
  const params = useParams();
  const projectId = Number(params.id);

  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedFormat, setSelectedFormat] = useState<ExportFormat>('csv');
  const [selectedStyle, setSelectedStyle] = useState<CitationStyle>('apa');
  const [exporting, setExporting] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    async function fetchProject() {
      try {
        const projectData = await apiClient.getProject(projectId);
        setProject(projectData);
      } catch (err) {
        setError('Failed to load project');
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    fetchProject();
  }, [projectId]);

  const handlePreview = async () => {
    setExporting(true);
    try {
      const previewData = await apiClient.previewExport(projectId, selectedFormat);
      setPreview(previewData);
    } catch (err) {
      console.error('Preview failed:', err);
      setPreview('Preview not available');
    } finally {
      setExporting(false);
    }
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      const result = await apiClient.exportDocuments({
        project_id: projectId,
        format: selectedFormat,
        citation_style: selectedFormat === 'bibtex' ? 'bibtex' : selectedStyle,
      });

      // Create download
      const blob = new Blob([result], {
        type: selectedFormat === 'json' ? 'application/json' : 'text/plain',
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${project?.name || 'export'}.${
        selectedFormat === 'markdown' || selectedFormat === 'annotated'
          ? 'md'
          : selectedFormat
      }`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Export failed:', err);
      setError('Export failed. Please try again.');
    } finally {
      setExporting(false);
    }
  };

  const handleCopy = async () => {
    if (preview) {
      await navigator.clipboard.writeText(preview);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !project) {
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
          <h1 className="text-2xl font-bold">Export</h1>
          <p className="text-muted-foreground">{project.name}</p>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Export Options */}
        <div className="space-y-6">
          {/* Format Selection */}
          <div className="border rounded-lg p-6">
            <h2 className="text-lg font-semibold mb-4">Export Format</h2>
            <div className="space-y-2">
              {(Object.keys(formatDescriptions) as ExportFormat[]).map((format) => {
                const Icon = formatIcons[format];
                return (
                  <label
                    key={format}
                    className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer border transition-colors ${
                      selectedFormat === format
                        ? 'border-primary bg-primary/5'
                        : 'border-transparent hover:bg-muted'
                    }`}
                  >
                    <input
                      type="radio"
                      name="format"
                      value={format}
                      checked={selectedFormat === format}
                      onChange={() => setSelectedFormat(format)}
                      className="sr-only"
                    />
                    <Icon className="h-5 w-5 text-muted-foreground" />
                    <div>
                      <p className="font-medium uppercase">{format}</p>
                      <p className="text-sm text-muted-foreground">
                        {formatDescriptions[format]}
                      </p>
                    </div>
                  </label>
                );
              })}
            </div>
          </div>

          {/* Citation Style (for non-BibTeX formats) */}
          {selectedFormat !== 'bibtex' && (
            <div className="border rounded-lg p-6">
              <h2 className="text-lg font-semibold mb-4">Citation Style</h2>
              <select
                value={selectedStyle}
                onChange={(e) => setSelectedStyle(e.target.value as CitationStyle)}
                className="w-full px-3 py-2 border rounded-md bg-background"
              >
                {(Object.entries(citationStyleNames) as [CitationStyle, string][])
                  .filter(([key]) => key !== 'bibtex')
                  .map(([style, name]) => (
                    <option key={style} value={style}>
                      {name}
                    </option>
                  ))}
              </select>
            </div>
          )}

          {/* Export Actions */}
          <div className="flex gap-3">
            <button
              onClick={handlePreview}
              disabled={exporting}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2 border rounded-md hover:bg-muted transition-colors disabled:opacity-50"
            >
              {exporting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <FileText className="h-4 w-4" />
              )}
              Preview
            </button>
            <button
              onClick={handleExport}
              disabled={exporting}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50"
            >
              {exporting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Download className="h-4 w-4" />
              )}
              Export
            </button>
          </div>
        </div>

        {/* Preview */}
        <div className="border rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Preview</h2>
            {preview && (
              <button
                onClick={handleCopy}
                className="flex items-center gap-1 px-2 py-1 text-sm hover:bg-muted rounded transition-colors"
              >
                {copied ? (
                  <>
                    <Check className="h-4 w-4 text-green-500" />
                    Copied
                  </>
                ) : (
                  <>
                    <Copy className="h-4 w-4" />
                    Copy
                  </>
                )}
              </button>
            )}
          </div>
          {preview ? (
            <pre className="bg-muted p-4 rounded-lg overflow-auto max-h-96 text-sm font-mono whitespace-pre-wrap">
              {preview}
            </pre>
          ) : (
            <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
              <FileText className="h-12 w-12 mb-4" />
              <p>Click Preview to see export content</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
