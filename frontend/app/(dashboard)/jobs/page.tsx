'use client';

import { Suspense, useEffect, useState, useMemo, useCallback } from 'react';
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
  ChevronDown,
  ChevronUp,
  FileText,
  AlertTriangle,
  Lightbulb,
  BookOpen,
  Filter,
  Bookmark,
} from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import { useJobWebSocket } from '@/lib/use-websocket';
import type { Job, JobStatus, JobProgressSummary, ProgressLogEntry } from '@/types/api';

const statusIcons: Record<JobStatus, typeof Activity> = {
  pending: Clock,
  running: Activity,
  paused: Pause,
  completed: CheckCircle,
  failed: XCircle,
  cancelled: XCircle,
};

const statusColors: Record<JobStatus, string> = {
  pending: 'bg-gray-100 text-gray-700',
  running: 'bg-blue-100 text-blue-700',
  paused: 'bg-yellow-100 text-yellow-700',
  completed: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
  cancelled: 'bg-gray-100 text-gray-600',
};

function JobsPageContent() {
  const searchParams = useSearchParams();
  const projectId = searchParams.get('project_id');

  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<{
    total: number;
    running: number;
    completed: number;
    failed: number;
    pending: number;
  }>({ total: 0, running: 0, completed: 0, failed: 0, pending: 0 });
  const [filter, setFilter] = useState<string>('all');
  const [expandedJobs, setExpandedJobs] = useState<Set<number>>(new Set());
  const [jobSummaries, setJobSummaries] = useState<Map<number, JobProgressSummary>>(new Map());
  const [jobLogs, setJobLogs] = useState<Map<number, ProgressLogEntry[]>>(new Map());
  const [loadingProgress, setLoadingProgress] = useState<Set<number>>(new Set());
  const [logFilter, setLogFilter] = useState<string>('all');

  const toggleExpanded = async (jobId: number) => {
    setExpandedJobs(prev => {
      const next = new Set(prev);
      if (next.has(jobId)) {
        next.delete(jobId);
      } else {
        next.add(jobId);
        // Load progress data when expanding
        loadJobProgress(jobId);
      }
      return next;
    });
  };

  const loadJobProgress = async (jobId: number) => {
    if (loadingProgress.has(jobId)) return;
    setLoadingProgress(prev => new Set(prev).add(jobId));
    try {
      const [summary, logs] = await Promise.all([
        apiClient.getJobProgressSummary(jobId),
        apiClient.getJobProgressLogs(jobId, { page_size: 100 }),
      ]);
      setJobSummaries(prev => new Map(prev).set(jobId, summary));
      setJobLogs(prev => new Map(prev).set(jobId, logs.entries));
    } catch (err) {
      console.error('Failed to load job progress:', err);
    } finally {
      setLoadingProgress(prev => {
        const next = new Set(prev);
        next.delete(jobId);
        return next;
      });
    }
  };

  const getFilteredLogs = (jobId: number): ProgressLogEntry[] => {
    const logs = jobLogs.get(jobId) || [];
    if (logFilter === 'all') return logs;
    return logs.filter(log => log.entry_type === logFilter);
  };

  const getLogIcon = (entryType: string) => {
    switch (entryType) {
      case 'phase_start':
      case 'phase_complete':
        return <Bookmark className="h-3 w-3" />;
      case 'paper_found':
      case 'paper_collected':
      case 'paper_processed':
        return <BookOpen className="h-3 w-3" />;
      case 'insight':
      case 'theme':
        return <Lightbulb className="h-3 w-3" />;
      case 'error':
        return <AlertTriangle className="h-3 w-3 text-red-500" />;
      case 'checkpoint':
        return <CheckCircle className="h-3 w-3 text-green-500" />;
      default:
        return <FileText className="h-3 w-3" />;
    }
  };

  const getLogColor = (entryType: string): string => {
    switch (entryType) {
      case 'phase_start':
      case 'phase_complete':
        return 'bg-blue-50 border-blue-200';
      case 'insight':
      case 'theme':
        return 'bg-yellow-50 border-yellow-200';
      case 'error':
        return 'bg-red-50 border-red-200';
      case 'checkpoint':
        return 'bg-green-50 border-green-200';
      default:
        return 'bg-gray-50 border-gray-200';
    }
  };

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
      // Map backend stats shape to frontend expected shape
      const byStatus = (statsData as { total_jobs?: number; by_status?: Record<string, number> }).by_status || {};
      setStats({
        total: (statsData as { total_jobs?: number }).total_jobs || 0,
        running: byStatus.running || 0,
        completed: byStatus.completed || 0,
        failed: byStatus.failed || 0,
        pending: byStatus.pending || 0,
      });
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
          progress_message: wsUpdate.message || job.progress_message,
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
            const isExpanded = expandedJobs.has(job.id);
            return (
              <div key={job.id} className="border rounded-lg overflow-hidden">
                <div className="p-4">
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
                          <p className="font-medium">{job.name || job.job_type.replace(/_/g, ' ')}</p>
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
                      <button
                        onClick={() => toggleExpanded(job.id)}
                        className="p-1 hover:bg-muted rounded"
                        title={isExpanded ? 'Collapse' : 'Expand'}
                      >
                        {isExpanded ? (
                          <ChevronUp className="h-4 w-4 text-muted-foreground" />
                        ) : (
                          <ChevronDown className="h-4 w-4 text-muted-foreground" />
                        )}
                      </button>
                    </div>
                  </div>
                  {job.status === 'running' && (
                    <div className="mt-3">
                      <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
                        <span>{job.progress_message || 'Processing...'}</span>
                        <span>{Math.round(job.progress * 100)}%</span>
                      </div>
                      <div className="h-2 bg-muted rounded overflow-hidden">
                        <div
                          className="h-full bg-primary transition-all duration-300"
                          style={{ width: `${job.progress * 100}%` }}
                        />
                      </div>
                    </div>
                  )}
                  {job.status === 'failed' && job.error_message && (
                    <div className="mt-2 flex items-start gap-2 text-sm text-red-600">
                      <AlertTriangle className="h-4 w-4 mt-0.5 flex-shrink-0" />
                      <p>{job.error_message}</p>
                    </div>
                  )}
                </div>

                {/* Expanded Details */}
                {isExpanded && (
                  <div className="border-t bg-muted/30 p-4 space-y-4">
                    {loadingProgress.has(job.id) ? (
                      <div className="flex items-center justify-center py-8">
                        <Loader2 className="h-6 w-6 animate-spin" />
                      </div>
                    ) : (
                      <>
                        {/* Progress Summary */}
                        {jobSummaries.has(job.id) && (
                          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
                            <div className="bg-background p-3 rounded-lg border">
                              <p className="text-xs text-muted-foreground">Papers Found</p>
                              <p className="text-xl font-bold">{jobSummaries.get(job.id)?.papers_found || 0}</p>
                            </div>
                            <div className="bg-background p-3 rounded-lg border">
                              <p className="text-xs text-muted-foreground">Collected</p>
                              <p className="text-xl font-bold">{jobSummaries.get(job.id)?.papers_collected || 0}</p>
                            </div>
                            <div className="bg-background p-3 rounded-lg border">
                              <p className="text-xs text-muted-foreground">Processed</p>
                              <p className="text-xl font-bold">{jobSummaries.get(job.id)?.papers_processed || 0}</p>
                            </div>
                            <div className="bg-background p-3 rounded-lg border">
                              <p className="text-xs text-muted-foreground">Insights</p>
                              <p className="text-xl font-bold text-yellow-600">{jobSummaries.get(job.id)?.insights_count || 0}</p>
                            </div>
                            <div className="bg-background p-3 rounded-lg border">
                              <p className="text-xs text-muted-foreground">Themes</p>
                              <p className="text-xl font-bold text-purple-600">{jobSummaries.get(job.id)?.themes_count || 0}</p>
                            </div>
                            <div className="bg-background p-3 rounded-lg border">
                              <p className="text-xs text-muted-foreground">Errors</p>
                              <p className={`text-xl font-bold ${(jobSummaries.get(job.id)?.errors_count || 0) > 0 ? 'text-red-600' : ''}`}>
                                {jobSummaries.get(job.id)?.errors_count || 0}
                              </p>
                            </div>
                            <div className="bg-background p-3 rounded-lg border">
                              <p className="text-xs text-muted-foreground">Checkpoint</p>
                              <p className="text-xl font-bold">
                                {jobSummaries.get(job.id)?.has_checkpoint ? (
                                  <CheckCircle className="h-5 w-5 text-green-500" />
                                ) : (
                                  <span className="text-muted-foreground">-</span>
                                )}
                              </p>
                            </div>
                          </div>
                        )}

                        {/* Phase Timeline */}
                        {jobSummaries.has(job.id) && (jobSummaries.get(job.id)?.phases_completed?.length || 0) > 0 && (
                          <div>
                            <p className="text-sm font-medium mb-2">Phases</p>
                            <div className="flex flex-wrap gap-2">
                              {jobSummaries.get(job.id)?.phases_completed.map((phase, idx) => (
                                <span key={idx} className="px-2 py-1 bg-green-100 text-green-700 rounded text-xs">
                                  {phase}
                                </span>
                              ))}
                              {jobSummaries.get(job.id)?.current_phase && (
                                <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs animate-pulse">
                                  {jobSummaries.get(job.id)?.current_phase} (in progress)
                                </span>
                              )}
                            </div>
                          </div>
                        )}

                        {/* Basic Progress Details */}
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
                          <div>
                            <p className="text-muted-foreground">Current Step</p>
                            <p className="font-medium">{job.current_step} / {job.total_steps}</p>
                          </div>
                          <div>
                            <p className="text-muted-foreground">Items Processed</p>
                            <p className="font-medium">{job.items_processed} / {job.items_total}</p>
                          </div>
                          <div>
                            <p className="text-muted-foreground">Items Failed</p>
                            <p className={`font-medium ${job.items_failed > 0 ? 'text-red-600' : ''}`}>
                              {job.items_failed}
                            </p>
                          </div>
                          <div>
                            <p className="text-muted-foreground">Priority</p>
                            <p className="font-medium capitalize">{job.priority}</p>
                          </div>
                        </div>

                        {/* Timing */}
                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-sm">
                          <div>
                            <p className="text-muted-foreground">Created</p>
                            <p className="font-medium">{new Date(job.created_at).toLocaleString()}</p>
                          </div>
                          {job.started_at && (
                            <div>
                              <p className="text-muted-foreground">Started</p>
                              <p className="font-medium">{new Date(job.started_at).toLocaleString()}</p>
                            </div>
                          )}
                          {job.completed_at && (
                            <div>
                              <p className="text-muted-foreground">Completed</p>
                              <p className="font-medium">{new Date(job.completed_at).toLocaleString()}</p>
                            </div>
                          )}
                        </div>

                        {/* Progress Log Stream */}
                        {jobLogs.has(job.id) && (jobLogs.get(job.id)?.length || 0) > 0 && (
                          <div>
                            <div className="flex items-center justify-between mb-2">
                              <p className="text-sm font-medium flex items-center gap-1">
                                <FileText className="h-4 w-4" />
                                Progress Log ({jobLogs.get(job.id)?.length} entries)
                              </p>
                              <div className="flex items-center gap-2">
                                <Filter className="h-3 w-3 text-muted-foreground" />
                                <select
                                  value={logFilter}
                                  onChange={(e) => setLogFilter(e.target.value)}
                                  className="text-xs border rounded px-2 py-1 bg-background"
                                >
                                  <option value="all">All</option>
                                  <option value="phase_start">Phases</option>
                                  <option value="paper_found">Papers</option>
                                  <option value="insight">Insights</option>
                                  <option value="error">Errors</option>
                                  <option value="checkpoint">Checkpoints</option>
                                </select>
                              </div>
                            </div>
                            <div className="max-h-60 overflow-auto space-y-1 bg-background rounded-lg border p-2">
                              {getFilteredLogs(job.id).slice(0, 50).map((entry) => (
                                <div
                                  key={entry.id}
                                  className={`flex items-start gap-2 p-2 rounded text-xs border ${getLogColor(entry.entry_type)}`}
                                >
                                  <span className="mt-0.5">{getLogIcon(entry.entry_type)}</span>
                                  <div className="flex-1 min-w-0">
                                    <p className="font-medium">{entry.message}</p>
                                    <p className="text-muted-foreground">
                                      {new Date(entry.created_at).toLocaleTimeString()}
                                      {entry.phase && ` • ${entry.phase}`}
                                    </p>
                                  </div>
                                  {entry.is_checkpoint && (
                                    <span className="px-1.5 py-0.5 bg-green-500 text-white rounded text-[10px]">
                                      Checkpoint
                                    </span>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Result Data */}
                        {job.result_data && Object.keys(job.result_data).length > 0 && (
                          <div>
                            <p className="text-sm text-muted-foreground mb-2 flex items-center gap-1">
                              <FileText className="h-4 w-4" />
                              Result Data
                            </p>
                            <pre className="text-xs bg-muted p-3 rounded overflow-auto max-h-40">
                              {JSON.stringify(job.result_data, null, 2)}
                            </pre>
                          </div>
                        )}

                        {/* Description */}
                        {job.description && (
                          <div>
                            <p className="text-sm text-muted-foreground mb-1">Description</p>
                            <p className="text-sm">{job.description}</p>
                          </div>
                        )}

                        {/* Actions for paused jobs */}
                        {job.status === 'paused' && (
                          <div className="flex items-center gap-2 pt-2 border-t">
                            <button
                              onClick={() => handleResume(job.id)}
                              className="flex items-center gap-2 px-3 py-1.5 bg-primary text-primary-foreground rounded-md text-sm hover:bg-primary/90 transition-colors"
                            >
                              <Play className="h-4 w-4" />
                              Resume from Checkpoint
                            </button>
                            {jobSummaries.get(job.id)?.latest_checkpoint_at && (
                              <p className="text-xs text-muted-foreground">
                                Last checkpoint: {new Date(jobSummaries.get(job.id)!.latest_checkpoint_at!).toLocaleString()}
                              </p>
                            )}
                          </div>
                        )}
                      </>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default function JobsPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    }>
      <JobsPageContent />
    </Suspense>
  );
}
