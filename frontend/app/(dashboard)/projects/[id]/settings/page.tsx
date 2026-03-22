'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Settings,
  Loader2,
  AlertCircle,
  Save,
  Trash2,
  Archive,
  AlertTriangle,
  X,
  Plus,
} from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import type { Project, ProjectStatus, ProjectScope } from '@/types/api';

// Valid status transitions (must match backend)
const validTransitions: Record<ProjectStatus, ProjectStatus[]> = {
  draft: ['clarifying', 'archived'],
  clarifying: ['ready', 'draft', 'archived'],
  ready: ['active', 'clarifying', 'archived'],
  active: ['completed', 'ready', 'archived'],
  completed: ['archived', 'active'],
  archived: ['draft'],
};

const statusOptions: { value: ProjectStatus; label: string; description: string }[] = [
  { value: 'draft', label: 'Draft', description: 'Initial setup, not started' },
  { value: 'clarifying', label: 'Clarifying', description: 'Refining research scope' },
  { value: 'ready', label: 'Ready', description: 'Ready to start research' },
  { value: 'active', label: 'Active', description: 'Research in progress' },
  { value: 'completed', label: 'Completed', description: 'Research complete' },
  { value: 'archived', label: 'Archived', description: 'Project archived' },
];

const LANGUAGE_OPTIONS = [
  { value: 'en', label: 'English' },
  { value: 'es', label: 'Spanish' },
  { value: 'fr', label: 'French' },
  { value: 'de', label: 'German' },
  { value: 'zh', label: 'Chinese' },
  { value: 'ja', label: 'Japanese' },
  { value: 'pt', label: 'Portuguese' },
  { value: 'ru', label: 'Russian' },
  { value: 'ar', label: 'Arabic' },
  { value: 'ko', label: 'Korean' },
];

const DOCUMENT_TYPE_OPTIONS = [
  { value: 'article', label: 'Journal Article' },
  { value: 'review', label: 'Review' },
  { value: 'book', label: 'Book' },
  { value: 'book-chapter', label: 'Book Chapter' },
  { value: 'conference-paper', label: 'Conference Paper' },
  { value: 'preprint', label: 'Preprint' },
  { value: 'thesis', label: 'Thesis' },
  { value: 'report', label: 'Report' },
];

const DISCIPLINE_OPTIONS = [
  'Computer Science',
  'Medicine',
  'Biology',
  'Physics',
  'Chemistry',
  'Mathematics',
  'Psychology',
  'Economics',
  'Engineering',
  'Environmental Science',
  'Materials Science',
  'Sociology',
  'Political Science',
  'Philosophy',
  'History',
  'Linguistics',
  'Education',
  'Law',
];

function TagInput({
  value,
  onChange,
  placeholder,
}: {
  value: string[];
  onChange: (tags: string[]) => void;
  placeholder?: string;
}) {
  const [input, setInput] = useState('');

  const handleAdd = () => {
    const trimmed = input.trim();
    if (trimmed && !value.includes(trimmed)) {
      onChange([...value, trimmed]);
      setInput('');
    }
  };

  const handleRemove = (tag: string) => {
    onChange(value.filter((t) => t !== tag));
  };

  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              handleAdd();
            }
          }}
          placeholder={placeholder}
          className="flex-1 px-3 py-1.5 border rounded-md bg-background text-sm"
        />
        <button
          type="button"
          onClick={handleAdd}
          className="px-3 py-1.5 border rounded-md hover:bg-muted transition-colors"
        >
          <Plus className="h-4 w-4" />
        </button>
      </div>
      {value.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {value.map((tag) => (
            <span
              key={tag}
              className="flex items-center gap-1 px-2 py-0.5 bg-muted rounded text-sm"
            >
              {tag}
              <button
                type="button"
                onClick={() => handleRemove(tag)}
                className="hover:text-destructive"
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export default function ProjectSettingsPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = Number(params.id);

  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Form state - General
  const [name, setName] = useState('');
  const [objective, setObjective] = useState('');
  const [status, setStatus] = useState<ProjectStatus>('draft');

  // Form state - Scope
  const [keywords, setKeywords] = useState<string[]>([]);
  const [excludedKeywords, setExcludedKeywords] = useState<string[]>([]);
  const [disciplines, setDisciplines] = useState<string[]>([]);
  const [yearFrom, setYearFrom] = useState('');
  const [yearTo, setYearTo] = useState('');
  const [languages, setLanguages] = useState<string[]>([]);
  const [documentTypes, setDocumentTypes] = useState<string[]>([]);
  const [minCitations, setMinCitations] = useState('');
  const [includePreprints, setIncludePreprints] = useState(true);
  const [specificJournals, setSpecificJournals] = useState<string[]>([]);
  const [specificAuthors, setSpecificAuthors] = useState<string[]>([]);
  const [geographicFocus, setGeographicFocus] = useState<string[]>([]);

  useEffect(() => {
    async function fetchProject() {
      try {
        const projectData = await apiClient.getProject(projectId);
        setProject(projectData);
        setName(projectData.name);
        setObjective(projectData.research_objective || '');
        setStatus(projectData.status);
        if (projectData.scope) {
          setKeywords(projectData.scope.keywords || []);
          setExcludedKeywords(projectData.scope.excluded_keywords || []);
          setDisciplines(projectData.scope.disciplines || []);
          setYearFrom(projectData.scope.date_range_start?.substring(0, 4) || '');
          setYearTo(projectData.scope.date_range_end?.substring(0, 4) || '');
          setLanguages(projectData.scope.languages || []);
          setDocumentTypes(projectData.scope.document_types || []);
          setMinCitations(projectData.scope.min_citations?.toString() || '');
          setIncludePreprints(projectData.scope.include_preprints ?? true);
          setSpecificJournals(projectData.scope.specific_journals || []);
          setSpecificAuthors(projectData.scope.specific_authors || []);
          setGeographicFocus(projectData.scope.geographic_focus || []);
        }
      } catch (err) {
        setError('Failed to load project');
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    fetchProject();
  }, [projectId]);

  const getAvailableStatuses = (): ProjectStatus[] => {
    if (!project) return [];
    const transitions = validTransitions[project.status] || [];
    return [project.status, ...transitions];
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      await apiClient.updateProject(projectId, {
        name,
        research_objective: objective,
      });

      // Build scope object
      const scope: ProjectScope = {
        keywords: keywords.length > 0 ? keywords : undefined,
        excluded_keywords: excludedKeywords.length > 0 ? excludedKeywords : undefined,
        disciplines: disciplines.length > 0 ? disciplines : undefined,
        date_range_start: yearFrom ? `${yearFrom}-01-01` : undefined,
        date_range_end: yearTo ? `${yearTo}-12-31` : undefined,
        languages: languages.length > 0 ? languages : undefined,
        document_types: documentTypes.length > 0 ? documentTypes : undefined,
        min_citations: minCitations ? Number(minCitations) : undefined,
        include_preprints: includePreprints,
        specific_journals: specificJournals.length > 0 ? specificJournals : undefined,
        specific_authors: specificAuthors.length > 0 ? specificAuthors : undefined,
        geographic_focus: geographicFocus.length > 0 ? geographicFocus : undefined,
      };

      await apiClient.updateProjectScope(projectId, scope);

      // Update status if changed
      if (status !== project?.status) {
        await apiClient.updateProjectStatus(projectId, status);
      }

      setSuccess('Settings saved successfully');
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      const apiError = err as { detail?: string; message?: string };
      const errorMsg = apiError.detail || apiError.message || 'Failed to save settings';
      setError(errorMsg);
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  const handleArchive = async () => {
    if (!confirm('Are you sure you want to archive this project?')) return;

    setSaving(true);
    try {
      await apiClient.updateProjectStatus(projectId, 'archived');
      setStatus('archived');
      setSuccess('Project archived');
    } catch (err) {
      setError('Failed to archive project');
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (
      !confirm(
        'Are you sure you want to delete this project? This action cannot be undone.'
      )
    )
      return;

    setDeleting(true);
    try {
      await apiClient.deleteProject(projectId);
      router.push('/projects');
    } catch (err) {
      setError('Failed to delete project');
      console.error(err);
      setDeleting(false);
    }
  };

  const toggleDiscipline = (discipline: string) => {
    setDisciplines((prev) =>
      prev.includes(discipline)
        ? prev.filter((d) => d !== discipline)
        : [...prev, discipline]
    );
  };

  const toggleLanguage = (lang: string) => {
    setLanguages((prev) =>
      prev.includes(lang) ? prev.filter((l) => l !== lang) : [...prev, lang]
    );
  };

  const toggleDocType = (docType: string) => {
    setDocumentTypes((prev) =>
      prev.includes(docType)
        ? prev.filter((d) => d !== docType)
        : [...prev, docType]
    );
  };

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
        <p className="text-muted-foreground">{error}</p>
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
    <div className="space-y-6 max-w-3xl">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          href={`/projects/${projectId}`}
          className="p-2 hover:bg-muted rounded-md transition-colors"
        >
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold">Project Settings</h1>
          <p className="text-muted-foreground">{project?.name}</p>
        </div>
      </div>

      {/* Notifications */}
      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-50 text-red-700 rounded-md">
          <AlertCircle className="h-4 w-4" />
          {error}
        </div>
      )}
      {success && (
        <div className="flex items-center gap-2 p-3 bg-green-50 text-green-700 rounded-md">
          <Save className="h-4 w-4" />
          {success}
        </div>
      )}

      {/* General Settings */}
      <div className="border rounded-lg p-6 space-y-4">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Settings className="h-5 w-5" />
          General
        </h2>

        <div>
          <label className="block text-sm font-medium mb-1">Project Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-3 py-2 border rounded-md bg-background"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Research Objective</label>
          <textarea
            value={objective}
            onChange={(e) => setObjective(e.target.value)}
            rows={3}
            className="w-full px-3 py-2 border rounded-md bg-background resize-none"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Status</label>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value as ProjectStatus)}
            className="w-full px-3 py-2 border rounded-md bg-background"
          >
            {statusOptions
              .filter((opt) => getAvailableStatuses().includes(opt.value))
              .map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label} - {opt.description}
                </option>
              ))}
          </select>
          <p className="text-xs text-muted-foreground mt-1">
            Only valid status transitions are shown
          </p>
        </div>
      </div>

      {/* Research Scope - Keywords */}
      <div className="border rounded-lg p-6 space-y-4">
        <h2 className="text-lg font-semibold">Keywords & Topics</h2>

        <div>
          <label className="block text-sm font-medium mb-1">Search Keywords</label>
          <TagInput
            value={keywords}
            onChange={setKeywords}
            placeholder="Add keyword and press Enter"
          />
          <p className="text-xs text-muted-foreground mt-1">
            Keywords to search for in academic databases
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Excluded Keywords</label>
          <TagInput
            value={excludedKeywords}
            onChange={setExcludedKeywords}
            placeholder="Add excluded keyword"
          />
          <p className="text-xs text-muted-foreground mt-1">
            Papers containing these keywords will be excluded
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Disciplines</label>
          <div className="flex flex-wrap gap-2">
            {DISCIPLINE_OPTIONS.map((discipline) => (
              <button
                key={discipline}
                type="button"
                onClick={() => toggleDiscipline(discipline)}
                className={`px-3 py-1 rounded-full text-sm transition-colors ${
                  disciplines.includes(discipline)
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted hover:bg-muted/80'
                }`}
              >
                {discipline}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Research Scope - Filters */}
      <div className="border rounded-lg p-6 space-y-4">
        <h2 className="text-lg font-semibold">Search Filters</h2>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Year From</label>
            <input
              type="number"
              value={yearFrom}
              onChange={(e) => setYearFrom(e.target.value)}
              placeholder="2020"
              min="1900"
              max="2030"
              className="w-full px-3 py-2 border rounded-md bg-background"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Year To</label>
            <input
              type="number"
              value={yearTo}
              onChange={(e) => setYearTo(e.target.value)}
              placeholder="2024"
              min="1900"
              max="2030"
              className="w-full px-3 py-2 border rounded-md bg-background"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Minimum Citations</label>
          <input
            type="number"
            value={minCitations}
            onChange={(e) => setMinCitations(e.target.value)}
            placeholder="0"
            min="0"
            className="w-full px-3 py-2 border rounded-md bg-background"
          />
          <p className="text-xs text-muted-foreground mt-1">
            Only include papers with at least this many citations
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Languages</label>
          <div className="flex flex-wrap gap-2">
            {LANGUAGE_OPTIONS.map((lang) => (
              <button
                key={lang.value}
                type="button"
                onClick={() => toggleLanguage(lang.value)}
                className={`px-3 py-1 rounded-full text-sm transition-colors ${
                  languages.includes(lang.value)
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted hover:bg-muted/80'
                }`}
              >
                {lang.label}
              </button>
            ))}
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            {languages.length === 0 ? 'All languages' : `${languages.length} selected`}
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Document Types</label>
          <div className="flex flex-wrap gap-2">
            {DOCUMENT_TYPE_OPTIONS.map((docType) => (
              <button
                key={docType.value}
                type="button"
                onClick={() => toggleDocType(docType.value)}
                className={`px-3 py-1 rounded-full text-sm transition-colors ${
                  documentTypes.includes(docType.value)
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted hover:bg-muted/80'
                }`}
              >
                {docType.label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="includePreprints"
            checked={includePreprints}
            onChange={(e) => setIncludePreprints(e.target.checked)}
            className="rounded"
          />
          <label htmlFor="includePreprints" className="text-sm font-medium">
            Include Preprints
          </label>
        </div>
      </div>

      {/* Research Scope - Specific Sources */}
      <div className="border rounded-lg p-6 space-y-4">
        <h2 className="text-lg font-semibold">Target Sources</h2>

        <div>
          <label className="block text-sm font-medium mb-1">Specific Journals</label>
          <TagInput
            value={specificJournals}
            onChange={setSpecificJournals}
            placeholder="Add journal name"
          />
          <p className="text-xs text-muted-foreground mt-1">
            Prioritize papers from these journals
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Specific Authors</label>
          <TagInput
            value={specificAuthors}
            onChange={setSpecificAuthors}
            placeholder="Add author name"
          />
          <p className="text-xs text-muted-foreground mt-1">
            Prioritize papers from these authors
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Geographic Focus</label>
          <TagInput
            value={geographicFocus}
            onChange={setGeographicFocus}
            placeholder="Add country or region"
          />
          <p className="text-xs text-muted-foreground mt-1">
            Focus on research from specific geographic areas
          </p>
        </div>
      </div>

      {/* Save Button */}
      <button
        onClick={handleSave}
        disabled={saving}
        className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50"
      >
        {saving ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <Save className="h-4 w-4" />
        )}
        Save Changes
      </button>

      {/* Danger Zone */}
      <div className="border border-red-200 rounded-lg p-6 space-y-4">
        <h2 className="text-lg font-semibold text-red-600 flex items-center gap-2">
          <AlertTriangle className="h-5 w-5" />
          Danger Zone
        </h2>

        <div className="flex items-center justify-between p-3 bg-red-50 rounded-md">
          <div>
            <p className="font-medium">Archive Project</p>
            <p className="text-sm text-muted-foreground">
              Hide from active projects list
            </p>
          </div>
          <button
            onClick={handleArchive}
            disabled={saving || status === 'archived'}
            className="flex items-center gap-2 px-3 py-1 border border-red-200 text-red-600 rounded-md hover:bg-red-100 transition-colors disabled:opacity-50"
          >
            <Archive className="h-4 w-4" />
            Archive
          </button>
        </div>

        <div className="flex items-center justify-between p-3 bg-red-50 rounded-md">
          <div>
            <p className="font-medium">Delete Project</p>
            <p className="text-sm text-muted-foreground">
              Permanently delete project and all documents
            </p>
          </div>
          <button
            onClick={handleDelete}
            disabled={deleting}
            className="flex items-center gap-2 px-3 py-1 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors disabled:opacity-50"
          >
            {deleting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Trash2 className="h-4 w-4" />
            )}
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}
