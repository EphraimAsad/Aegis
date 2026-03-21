'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  BookOpen,
  FolderKanban,
  FileText,
  Activity,
  ArrowRight,
  TrendingUp,
  Loader2,
} from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import type { Project, Job, HealthResponse } from '@/types/api';

export default function DashboardPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchDashboardData() {
      try {
        const [healthData, projectsData, jobsData] = await Promise.all([
          apiClient.health().catch(() => null),
          apiClient.getProjects(1, 5).catch(() => ({ items: [] })),
          apiClient.getJobs(undefined, 'running', 1, 5).catch(() => ({ items: [] })),
        ]);
        setHealth(healthData);
        setProjects(projectsData.items);
        setJobs(jobsData.items);
      } catch (err) {
        console.error('Dashboard fetch error:', err);
      } finally {
        setLoading(false);
      }
    }
    fetchDashboardData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Welcome Header */}
      <div>
        <h1 className="text-3xl font-bold">Welcome to Aegis</h1>
        <p className="text-muted-foreground mt-2">
          Your research-focused AI assistant for academic literature review
        </p>
      </div>

      {/* Quick Stats */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="border rounded-lg p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary/10 rounded-lg">
              <FolderKanban className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-2xl font-bold">{projects.length}</p>
              <p className="text-sm text-muted-foreground">Active Projects</p>
            </div>
          </div>
        </div>
        <div className="border rounded-lg p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-500/10 rounded-lg">
              <Activity className="h-5 w-5 text-blue-500" />
            </div>
            <div>
              <p className="text-2xl font-bold">{jobs.length}</p>
              <p className="text-sm text-muted-foreground">Running Jobs</p>
            </div>
          </div>
        </div>
        <div className="border rounded-lg p-4">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${
              health?.status === 'healthy' ? 'bg-green-500/10' : 'bg-yellow-500/10'
            }`}>
              <TrendingUp className={`h-5 w-5 ${
                health?.status === 'healthy' ? 'text-green-500' : 'text-yellow-500'
              }`} />
            </div>
            <div>
              <p className="text-2xl font-bold capitalize">{health?.status || 'Unknown'}</p>
              <p className="text-sm text-muted-foreground">System Status</p>
            </div>
          </div>
        </div>
        <div className="border rounded-lg p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-500/10 rounded-lg">
              <BookOpen className="h-5 w-5 text-purple-500" />
            </div>
            <div>
              <p className="text-2xl font-bold">{health?.version || '0.1.0'}</p>
              <p className="text-sm text-muted-foreground">Version</p>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid gap-6 md:grid-cols-2">
        <div className="border rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Quick Actions</h2>
          <div className="space-y-3">
            <Link
              href="/projects/new"
              className="flex items-center justify-between p-3 bg-muted/50 rounded-lg hover:bg-muted transition-colors"
            >
              <div className="flex items-center gap-3">
                <FolderKanban className="h-5 w-5 text-primary" />
                <span>Create New Project</span>
              </div>
              <ArrowRight className="h-4 w-4 text-muted-foreground" />
            </Link>
            <Link
              href="/search"
              className="flex items-center justify-between p-3 bg-muted/50 rounded-lg hover:bg-muted transition-colors"
            >
              <div className="flex items-center gap-3">
                <FileText className="h-5 w-5 text-primary" />
                <span>Search Academic Papers</span>
              </div>
              <ArrowRight className="h-4 w-4 text-muted-foreground" />
            </Link>
            <Link
              href="/jobs"
              className="flex items-center justify-between p-3 bg-muted/50 rounded-lg hover:bg-muted transition-colors"
            >
              <div className="flex items-center gap-3">
                <Activity className="h-5 w-5 text-primary" />
                <span>View Running Jobs</span>
              </div>
              <ArrowRight className="h-4 w-4 text-muted-foreground" />
            </Link>
          </div>
        </div>

        {/* Recent Projects */}
        <div className="border rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Recent Projects</h2>
            <Link href="/projects" className="text-sm text-primary hover:underline">
              View all
            </Link>
          </div>
          {projects.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <p>No projects yet</p>
              <Link href="/projects/new" className="text-primary hover:underline text-sm">
                Create your first project
              </Link>
            </div>
          ) : (
            <ul className="space-y-3">
              {projects.slice(0, 3).map((project) => (
                <li key={project.id}>
                  <Link
                    href={`/projects/${project.id}`}
                    className="flex items-center justify-between p-3 bg-muted/50 rounded-lg hover:bg-muted transition-colors"
                  >
                    <div>
                      <p className="font-medium">{project.name}</p>
                      <p className="text-sm text-muted-foreground truncate max-w-[250px]">
                        {project.research_objective}
                      </p>
                    </div>
                    <span className={`px-2 py-1 rounded text-xs ${
                      project.status === 'complete' ? 'bg-green-100 text-green-700' :
                      project.status === 'processing' ? 'bg-blue-100 text-blue-700' :
                      'bg-gray-100 text-gray-700'
                    }`}>
                      {project.status}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Running Jobs */}
      {jobs.length > 0 && (
        <div className="border rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Running Jobs</h2>
            <Link href="/jobs" className="text-sm text-primary hover:underline">
              View all
            </Link>
          </div>
          <div className="space-y-3">
            {jobs.map((job) => (
              <div key={job.id} className="p-3 bg-muted/50 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <p className="font-medium">{job.job_type.replace('_', ' ')}</p>
                  <span className="text-sm text-muted-foreground">{job.progress}%</span>
                </div>
                <div className="h-2 bg-muted rounded overflow-hidden">
                  <div
                    className="h-full bg-primary transition-all"
                    style={{ width: `${job.progress}%` }}
                  />
                </div>
                {job.message && (
                  <p className="text-xs text-muted-foreground mt-1">{job.message}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
