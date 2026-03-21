'use client';

import { useEffect, useState, useMemo, useCallback } from 'react';
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
  Wifi,
  WifiOff,
} from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import { useJobWebSocket } from '@/lib/use-websocket';
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

  // WebSocket for real-time updates
  const { status: wsStatus, subscribe, unsubscribe, jobUpdates } = useJobWebSocket();

  // Fetch jobs from API
  const fetchJobs = useCallback(async () => {
    try {
      const [jobsData, statsData] = await Promise.all([
        apiClient.getJobs(projectId ? Number(projectId) : undefined, filter === 'all' ? undefined : filter),
        apiClient.getJobStats(),
      ]);
      setJobs(jobsData.items);
      setStats(statsData);
      setError(null);
    } catch (err) {
      setError('Failed to load jobs');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [projectId, filter]);

  // Initial fetch and polling fallback
  useEffect(() => {
    fetchJobs();

    // Fallback polling (less frequent when WebSocket is connected)
    const interval = setInterval(
      fetchJobs,
      wsStatus === 'connected' ? 30000 : 5000
    );
    return () => clearInterval(interval);
  }, [fetchJobs, wsStatus]);

  // Subscribe to running jobs via WebSocket
  useEffect(() => {
    const runningJobs = jobs.filter(j => j.status === 'running');
    runningJobs.forEach(job => subscribe(job.id));

    return () => {
      runningJobs.forEach(job => unsubscribe(job.id));
    };
  }, [jobs, subscribe, unsubscribe]);

  // Merge WebSocket updates with job state
  const mergedJobs = useMemo(() => {
    return jobs.map(job => {
      const wsUpdate = jobUpdates.get(job.id);
      if (wsUpdate) {
        return {
          ...job,
          status: wsUpdate.status as JobStatus,
          progress: wsUpdate.progress,
          message: wsUpdate.message || job.message,
        };
      }
      return job;
    });
  }, [jobs, jobUpdates]);

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
      await fetchJobs();
    } catch (err) {
      console.error(err);
    }
  };

  const handleResume = async (jobId: number) => {
    try {
      await apiClient.resumeJob(jobId);
      await fetchJobs();
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Jobs</h1>
          <p className="text-muted-foreground">
            Monitor and manage background tasks
          </p>
        </div>
        {/* WebSocket Status Indicator */}
        <div className="flex items-center gap-2 text-sm">
          {wsStatus === 'connected' ? (
            <>
              <Wifi className="h-4 w-4 text-green-500" />
              <span className="text-green-600">Live</span>
            </>
          ) : wsStatus === 'connecting' ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              <span className="text-muted-foreground">Connecting...</span>
            </>
          ) : (
            <>
              <WifiOff className="h-4 w-4 text-muted-foreground" />
              <span className="text-muted-foreground">Polling</span>
            </>
          )}
        </div>
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
      {mergedJobs.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-64 border rounded-lg bg-muted/30">
          <Activity className="h-12 w-12 text-muted-foreground mb-4" />
          <p className="text-muted-foreground">No jobs found</p>
        </div>
      ) : (
        <div className="space-y-3">
          {mergedJobs.map((job) => {
            const StatusIcon = statusIcons[job.status];
            const hasLiveUpdate = jobUpdates.has(job.id);
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
                      <div className="flex items-center gap-2">
                        <p className="font-medium">{job.job_type.replace('_', ' ')}</p>
                        {hasLiveUpdate && (
                          <span className="flex h-2 w-2">
                            <span className="animate-ping absolute inline-flex h-2 w-2 rounded-full bg-green-400 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                          </span>
                        )}
                      </div>
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
                        className="h-full bg-primary transition-all duration-300"
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
