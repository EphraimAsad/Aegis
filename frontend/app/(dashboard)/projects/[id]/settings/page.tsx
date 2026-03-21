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
} from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import type { Project, ProjectStatus } from '@/types/api';

const statusOptions: { value: ProjectStatus; label: string; description: string }[] = [
  { value: 'draft', label: 'Draft', description: 'Initial setup, not started' },
  { value: 'clarifying', label: 'Clarifying', description: 'Refining research scope' },
  { value: 'ready', label: 'Ready', description: 'Ready to start research' },
  { value: 'searching', label: 'Searching', description: 'Searching for papers' },
  { value: 'processing', label: 'Processing', description: 'Processing documents' },
  { value: 'complete', label: 'Complete', description: 'Research complete' },
  { value: 'archived', label: 'Archived', description: 'Project archived' },
];

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

  // Form state
  const [name, setName] = useState('');
  const [objective, setObjective] = useState('');
  const [status, setStatus] = useState<ProjectStatus>('draft');
  const [keywords, setKeywords] = useState('');
  const [yearFrom, setYearFrom] = useState('');
  const [yearTo, setYearTo] = useState('');

  useEffect(() => {
    async function fetchProject() {
      try {
        const projectData = await apiClient.getProject(projectId);
        setProject(projectData);
        setName(projectData.name);
        setObjective(projectData.research_objective || '');
        setStatus(projectData.status);
        if (projectData.scope) {
          setKeywords(projectData.scope.keywords?.join(', ') || '');
          setYearFrom(projectData.scope.year_from?.toString() || '');
          setYearTo(projectData.scope.year_to?.toString() || '');
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

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      await apiClient.updateProject(projectId, {
        name,
        research_objective: objective,
      });

      // Update scope
      await apiClient.updateProjectScope(projectId, {
        keywords: keywords.split(',').map((k) => k.trim()).filter(Boolean),
        year_from: yearFrom ? Number(yearFrom) : undefined,
        year_to: yearTo ? Number(yearTo) : undefined,
      });

      // Update status if changed
      if (status !== project?.status) {
        await apiClient.updateProjectStatus(projectId, status);
      }

      setSuccess('Settings saved successfully');
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError('Failed to save settings');
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
    <div className="space-y-6 max-w-2xl">
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
            {statusOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label} - {opt.description}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Research Scope */}
      <div className="border rounded-lg p-6 space-y-4">
        <h2 className="text-lg font-semibold">Research Scope</h2>

        <div>
          <label className="block text-sm font-medium mb-1">Keywords</label>
          <input
            type="text"
            value={keywords}
            onChange={(e) => setKeywords(e.target.value)}
            placeholder="machine learning, neural networks, deep learning"
            className="w-full px-3 py-2 border rounded-md bg-background"
          />
          <p className="text-xs text-muted-foreground mt-1">
            Comma-separated keywords for paper search
          </p>
        </div>

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
