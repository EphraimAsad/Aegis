'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import {
  ArrowLeft,
  FileText,
  Play,
  Settings,
  Trash2,
  Loader2,
  AlertCircle,
  Download,
  Search,
  BarChart3,
  MessageCircle,
  HelpCircle,
} from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import type { Project, Document, Job, ProjectStatus, ClarificationQuestion } from '@/types/api';

const statusColors: Record<ProjectStatus, string> = {
  draft: 'bg-gray-100 text-gray-700',
  clarifying: 'bg-yellow-100 text-yellow-700',
  ready: 'bg-blue-100 text-blue-700',
  active: 'bg-purple-100 text-purple-700',
  completed: 'bg-green-100 text-green-700',
  archived: 'bg-gray-200 text-gray-600',
};

export default function ProjectDetailPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = Number(params.id);

  const [project, setProject] = useState<Project | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [clarifications, setClarifications] = useState<ClarificationQuestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [startingJob, setStartingJob] = useState(false);

  // Use backend readiness fields when available, fallback to local counting
  const unansweredQuestions = project?.unanswered_questions ?? clarifications.filter((q) => !q.is_answered).length;
  const isReadyForResearch = project?.is_ready_for_research ?? (unansweredQuestions === 0 && project?.status !== 'archived');

  useEffect(() => {
    async function fetchData() {
      try {
        const [projectData, docsData, jobsData, clarificationsData] = await Promise.all([
          apiClient.getProject(projectId),
          apiClient.getDocuments(projectId, 1, 10).catch(() => ({ items: [] })),
          apiClient.getJobs(projectId, undefined, 1, 5).catch(() => ({ items: [] })),
          apiClient.getClarifications(projectId).catch(() => []),
        ]);
        setProject(projectData);
        setDocuments(docsData.items);
        setJobs(jobsData.items);
        setClarifications(clarificationsData);
      } catch (err) {
        setError('Failed to load project');
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [projectId]);

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this project? This action cannot be undone.')) {
      return;
    }
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

  const handleStartResearch = async () => {
    setStartingJob(true);
    try {
      await apiClient.startResearchJob(projectId);
      // Refresh jobs
      const jobsData = await apiClient.getJobs(projectId, undefined, 1, 5);
      setJobs(jobsData.items);
    } catch (err) {
      setError('Failed to start research job');
      console.error(err);
    } finally {
      setStartingJob(false);
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
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-4">
          <Link
            href="/projects"
            className="p-2 hover:bg-muted rounded-md transition-colors mt-1"
          >
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-2xl font-bold">{project.name}</h1>
              <span className={`px-2 py-1 rounded text-xs font-medium ${statusColors[project.status]}`}>
                {project.status}
              </span>
            </div>
            <p className="text-muted-foreground max-w-2xl">
              {project.research_objective}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative group">
            <button
              onClick={handleStartResearch}
              disabled={startingJob || project.status === 'active' || !isReadyForResearch}
              className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50"
            >
              {startingJob ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              Start Research
            </button>
            {!isReadyForResearch && unansweredQuestions > 0 && (
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-1 bg-gray-900 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
                {unansweredQuestions} unanswered question{unansweredQuestions > 1 ? 's' : ''} remaining
              </div>
            )}
          </div>
          <button
            onClick={handleDelete}
            disabled={deleting}
            className="p-2 text-destructive hover:bg-destructive/10 rounded-md transition-colors"
          >
            {deleting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {/* Content Grid */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Documents */}
        <div className="border rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Documents
            </h2>
            <span className="text-sm text-muted-foreground">
              {documents.length} total
            </span>
          </div>
          {documents.length === 0 ? (
            <p className="text-sm text-muted-foreground py-8 text-center">
              No documents yet. Start a research job to find papers.
            </p>
          ) : (
            <ul className="space-y-2">
              {documents.slice(0, 5).map((doc) => (
                <li key={doc.id} className="text-sm p-2 bg-muted/30 rounded">
                  <p className="font-medium truncate">{doc.title}</p>
                  <p className="text-xs text-muted-foreground">
                    {doc.year} • {doc.status}
                  </p>
                </li>
              ))}
            </ul>
          )}
          {documents.length > 5 && (
            <Link
              href={`/projects/${projectId}/documents`}
              className="block mt-4 text-sm text-primary hover:underline text-center"
            >
              View all documents
            </Link>
          )}
        </div>

        {/* Recent Jobs */}
        <div className="border rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold flex items-center gap-2">
              <Settings className="h-4 w-4" />
              Recent Jobs
            </h2>
            <Link
              href={`/jobs?project_id=${projectId}`}
              className="text-sm text-primary hover:underline"
            >
              View all
            </Link>
          </div>
          {jobs.length === 0 ? (
            <p className="text-sm text-muted-foreground py-8 text-center">
              No jobs yet
            </p>
          ) : (
            <ul className="space-y-2">
              {jobs.map((job) => (
                <li key={job.id} className="text-sm p-2 bg-muted/30 rounded">
                  <div className="flex items-center justify-between">
                    <p className="font-medium">{job.job_type}</p>
                    <span className={`text-xs px-2 py-0.5 rounded ${
                      job.status === 'completed' ? 'bg-green-100 text-green-700' :
                      job.status === 'failed' ? 'bg-red-100 text-red-700' :
                      job.status === 'running' ? 'bg-blue-100 text-blue-700' :
                      'bg-gray-100 text-gray-700'
                    }`}>
                      {job.status}
                    </span>
                  </div>
                  {job.status === 'running' && (
                    <div className="mt-2 h-1 bg-muted rounded overflow-hidden">
                      <div
                        className="h-full bg-primary transition-all"
                        style={{ width: `${job.progress * 100}%` }}
                      />
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Clarifications Alert */}
        {unansweredQuestions > 0 && (
          <div className="border border-yellow-200 bg-yellow-50 rounded-lg p-4 md:col-span-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <HelpCircle className="h-5 w-5 text-yellow-600" />
                <div>
                  <p className="font-medium text-yellow-800">
                    {unansweredQuestions} Clarification Question{unansweredQuestions > 1 ? 's' : ''} Pending
                  </p>
                  <p className="text-sm text-yellow-600">
                    Answer these questions to refine your research scope before starting
                  </p>
                </div>
              </div>
              <Link
                href={`/projects/${projectId}/clarifications`}
                className="px-4 py-2 bg-yellow-600 text-white rounded-md hover:bg-yellow-700 transition-colors text-sm font-medium"
              >
                Answer Questions
              </Link>
            </div>
          </div>
        )}

        {/* Quick Actions */}
        <div className="border rounded-lg p-6 md:col-span-2">
          <h2 className="font-semibold mb-4">Quick Actions</h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <button
              onClick={handleStartResearch}
              disabled={startingJob || !isReadyForResearch}
              className="flex items-center gap-3 p-4 border rounded-lg hover:bg-muted/50 transition-colors text-left disabled:opacity-50"
            >
              <Search className="h-5 w-5 text-primary" />
              <div>
                <p className="font-medium text-sm">Search Papers</p>
                <p className="text-xs text-muted-foreground">Find relevant literature</p>
              </div>
            </button>
            <Link
              href={`/projects/${projectId}/clarifications`}
              className="flex items-center gap-3 p-4 border rounded-lg hover:bg-muted/50 transition-colors relative"
            >
              <MessageCircle className="h-5 w-5 text-primary" />
              <div>
                <p className="font-medium text-sm">Clarifications</p>
                <p className="text-xs text-muted-foreground">Refine research scope</p>
              </div>
              {unansweredQuestions > 0 && (
                <span className="absolute top-2 right-2 px-2 py-0.5 bg-yellow-500 text-white text-xs rounded-full">
                  {unansweredQuestions}
                </span>
              )}
            </Link>
            <Link
              href={`/projects/${projectId}/export`}
              className="flex items-center gap-3 p-4 border rounded-lg hover:bg-muted/50 transition-colors"
            >
              <Download className="h-5 w-5 text-primary" />
              <div>
                <p className="font-medium text-sm">Export</p>
                <p className="text-xs text-muted-foreground">Download as CSV, BibTeX, etc.</p>
              </div>
            </Link>
            <Link
              href={`/analytics?project_id=${projectId}`}
              className="flex items-center gap-3 p-4 border rounded-lg hover:bg-muted/50 transition-colors"
            >
              <BarChart3 className="h-5 w-5 text-primary" />
              <div>
                <p className="font-medium text-sm">Analytics</p>
                <p className="text-xs text-muted-foreground">View project statistics</p>
              </div>
            </Link>
            <Link
              href={`/projects/${projectId}/settings`}
              className="flex items-center gap-3 p-4 border rounded-lg hover:bg-muted/50 transition-colors"
            >
              <Settings className="h-5 w-5 text-primary" />
              <div>
                <p className="font-medium text-sm">Settings</p>
                <p className="text-xs text-muted-foreground">Configure project options</p>
              </div>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
