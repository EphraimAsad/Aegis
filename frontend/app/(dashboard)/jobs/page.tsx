'use client';

import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import {
  Activity,
  Loader2,
  AlertCircle,
  Play,
  Pause,
  RotateCcw,
  XCircle,
  CheckCircle,
  Clock,
} from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import type { Job, JobStatus } from '@/types/api';

const statusIcons: Record<JobStatus, typeof Activity> = {
  pending: Clock,
  queued: Clock,
  running: Activity,
  paused: Pause,
  completed: CheckCircle,
  failed: XCircle,
  cancelled: XCircle,
};

const statusColors: Record<JobStatus, string> = {
  pending: 'bg-gray-100 text-gray-700',
  queued: 'bg-blue-100 text-blue-700',
  running: 'bg-blue-100 text-blue-700',
  paused: 'bg-yellow-100 text-yellow-700',
  completed: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
  cancelled: 'bg-gray-100 text-gray-600',
};

export default function JobsPage() {
  const searchParams = useSearchParams();
  const projectId = searchParams.get('project_id');

  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<Record<string, number>>({});
  const [filter, setFilter] = useState<string>('all');

  useEffect(() => {
    async function fetchJobs() {
      try {
        const [jobsData, statsData] = await Promise.all([
          apiClient.getJobs(projectId ? Number(projectId) : undefined, filter === 'all' ? undefined : filter),
          apiClient.getJobStats(),
        ]);
        setJobs(jobsData.items);
        setStats(statsData);
      } catch (err) {
        setError('Failed to load jobs');
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    fetchJobs();

    // Refresh every 5 seconds for running jobs
    const interval = setInterval(fetchJobs, 5000);
    return () => clearInterval(interval);
  }, [projectId, filter]);

  const handleCancel = async (jobId: number) => {
    try {
      await apiClient.cancelJob(jobId);
      setJobs(jobs.map(j => j.id === jobId ? { ...j, status: 'cancelled' as JobStatus } : j));
    } catch (err) {
      console.error(err);
    }
  };

  const handleRetry = async (jobId: number) => {
    try {
      await apiClient.retryJob(jobId);
      // Refresh jobs
      const jobsData = await apiClient.getJobs(projectId ? Number(projectId) : undefined);
      setJobs(jobsData.items);
    } catch (err) {
      console.error(err);
    }
  };

  const handleResume = async (jobId: number) => {
    try {
      await apiClient.resumeJob(jobId);
      // Refresh jobs
      const jobsData = await apiClient.getJobs(projectId ? Number(projectId) : undefined);
      setJobs(jobsData.items);
    } catch (err) {
      console.error(err);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <AlertCircle className="h-12 w-12 text-destructive" />
        <p className="text-muted-foreground">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Jobs</h1>
        <p className="text-muted-foreground">
          Monitor and manage background tasks
        </p>
      </div>

      {/* Stats */}
      <div className="grid gap-4 sm:grid-cols-4">
        <div className="border rounded-lg p-4">
          <p className="text-sm text-muted-foreground">Total</p>
          <p className="text-2xl font-bold">{stats.total || 0}</p>
        </div>
        <div className="border rounded-lg p-4">
          <p className="text-sm text-muted-foreground">Running</p>
          <p className="text-2xl font-bold text-blue-600">{stats.running || 0}</p>
        </div>
        <div className="border rounded-lg p-4">
          <p className="text-sm text-muted-foreground">Completed</p>
          <p className="text-2xl font-bold text-green-600">{stats.completed || 0}</p>
        </div>
        <div className="border rounded-lg p-4">
          <p className="text-sm text-muted-foreground">Failed</p>
          <p className="text-2xl font-bold text-red-600">{stats.failed || 0}</p>
        </div>
      </div>

      {/* Filter */}
      <div className="flex gap-2">
        {['all', 'running', 'completed', 'failed', 'pending'].map((status) => (
          <button
            key={status}
            onClick={() => setFilter(status)}
            className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
              filter === status
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted text-muted-foreground hover:text-foreground'
            }`}
          >
            {status.charAt(0).toUpperCase() + status.slice(1)}
          </button>
        ))}
      </div>

      {/* Jobs List */}
      {jobs.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-64 border rounded-lg bg-muted/30">
          <Activity className="h-12 w-12 text-muted-foreground mb-4" />
          <p className="text-muted-foreground">No jobs found</p>
        </div>
      ) : (
        <div className="space-y-3">
          {jobs.map((job) => {
            const StatusIcon = statusIcons[job.status];
            return (
              <div key={job.id} className="border rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <StatusIcon className={`h-5 w-5 ${
                      job.status === 'running' ? 'text-blue-600 animate-pulse' :
                      job.status === 'completed' ? 'text-green-600' :
                      job.status === 'failed' ? 'text-red-600' :
                      'text-muted-foreground'
                    }`} />
                    <div>
                      <p className="font-medium">{job.job_type.replace('_', ' ')}</p>
                      <p className="text-sm text-muted-foreground">
                        Project #{job.project_id} • {new Date(job.created_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${statusColors[job.status]}`}>
                      {job.status}
                    </span>
                    {job.status === 'running' && (
                      <button
                        onClick={() => handleCancel(job.id)}
                        className="p-1 hover:bg-muted rounded"
                        title="Cancel"
                      >
                        <XCircle className="h-4 w-4 text-muted-foreground" />
                      </button>
                    )}
                    {job.status === 'failed' && (
                      <button
                        onClick={() => handleRetry(job.id)}
                        className="p-1 hover:bg-muted rounded"
                        title="Retry"
                      >
                        <RotateCcw className="h-4 w-4 text-muted-foreground" />
                      </button>
                    )}
                    {job.status === 'paused' && (
                      <button
                        onClick={() => handleResume(job.id)}
                        className="p-1 hover:bg-muted rounded"
                        title="Resume"
                      >
                        <Play className="h-4 w-4 text-muted-foreground" />
                      </button>
                    )}
                  </div>
                </div>
                {job.status === 'running' && (
                  <div className="mt-3">
                    <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
                      <span>{job.message || 'Processing...'}</span>
                      <span>{job.progress}%</span>
                    </div>
                    <div className="h-2 bg-muted rounded overflow-hidden">
                      <div
                        className="h-full bg-primary transition-all"
                        style={{ width: `${job.progress}%` }}
                      />
                    </div>
                  </div>
                )}
                {job.status === 'failed' && job.error_message && (
                  <p className="mt-2 text-sm text-red-600">{job.error_message}</p>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
