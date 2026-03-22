'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Plus, FolderKanban, ChevronRight, AlertCircle, Loader2 } from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import type { Project, ProjectStatus } from '@/types/api';

const statusColors: Record<ProjectStatus, string> = {
  draft: 'bg-gray-100 text-gray-700',
  clarifying: 'bg-yellow-100 text-yellow-700',
  ready: 'bg-blue-100 text-blue-700',
  active: 'bg-purple-100 text-purple-700',
  completed: 'bg-green-100 text-green-700',
  archived: 'bg-gray-200 text-gray-600',
};

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchProjects() {
      try {
        const response = await apiClient.getProjects();
        setProjects(response.items);
      } catch (err) {
        setError('Failed to load projects');
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    fetchProjects();
  }, []);

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
        <button
          onClick={() => window.location.reload()}
          className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Projects</h1>
          <p className="text-muted-foreground">
            Manage your research projects
          </p>
        </div>
        <Link
          href="/projects/new"
          className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors"
        >
          <Plus className="h-4 w-4" />
          New Project
        </Link>
      </div>

      {/* Projects Grid */}
      {projects.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-64 border rounded-lg bg-muted/30">
          <FolderKanban className="h-12 w-12 text-muted-foreground mb-4" />
          <p className="text-muted-foreground mb-4">No projects yet</p>
          <Link
            href="/projects/new"
            className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium"
          >
            <Plus className="h-4 w-4" />
            Create your first project
          </Link>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <Link
              key={project.id}
              href={`/projects/${project.id}`}
              className="block p-6 border rounded-lg hover:shadow-md transition-shadow bg-card"
            >
              <div className="flex items-start justify-between mb-3">
                <h3 className="font-semibold truncate pr-2">{project.name}</h3>
                <span className={`px-2 py-1 rounded text-xs font-medium ${statusColors[project.status]}`}>
                  {project.status}
                </span>
              </div>
              <p className="text-sm text-muted-foreground line-clamp-2 mb-4">
                {project.research_objective}
              </p>
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>
                  {new Date(project.created_at).toLocaleDateString()}
                </span>
                <ChevronRight className="h-4 w-4" />
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
