'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { apiClient } from '@/lib/api-client';

export default function NewProjectPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    research_objective: '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const project = await apiClient.createProject(formData);
      router.push(`/projects/${project.id}`);
    } catch (err) {
      setError('Failed to create project. Please try again.');
      console.error(err);
      setLoading(false);
    }
  };

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const isValid = formData.name.trim() && formData.research_objective.trim().length >= 10;

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          href="/projects"
          className="p-2 hover:bg-muted rounded-md transition-colors"
        >
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold">New Project</h1>
          <p className="text-muted-foreground">
            Create a new research project
          </p>
        </div>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-6">
        {error && (
          <div className="p-4 bg-destructive/10 text-destructive rounded-md text-sm">
            {error}
          </div>
        )}

        <div className="space-y-2">
          <label htmlFor="name" className="block text-sm font-medium">
            Project Name <span className="text-destructive">*</span>
          </label>
          <input
            type="text"
            id="name"
            name="name"
            value={formData.name}
            onChange={handleChange}
            placeholder="e.g., Climate Change Impact on Agriculture"
            className="w-full px-3 py-2 border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
            required
          />
        </div>

        <div className="space-y-2">
          <label htmlFor="description" className="block text-sm font-medium">
            Description
          </label>
          <textarea
            id="description"
            name="description"
            value={formData.description}
            onChange={handleChange}
            placeholder="Brief description of your research project..."
            rows={3}
            className="w-full px-3 py-2 border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary resize-none"
          />
        </div>

        <div className="space-y-2">
          <label htmlFor="research_objective" className="block text-sm font-medium">
            Research Objective <span className="text-destructive">*</span>
          </label>
          <textarea
            id="research_objective"
            name="research_objective"
            value={formData.research_objective}
            onChange={handleChange}
            placeholder="Describe what you want to investigate. Be specific about the research question, scope, and any particular focus areas..."
            rows={5}
            className="w-full px-3 py-2 border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary resize-none"
            required
            minLength={10}
          />
          <p className="text-xs text-muted-foreground">
            Minimum 10 characters. The more detail you provide, the better Aegis can help refine your search.
          </p>
        </div>

        <div className="flex items-center gap-4 pt-4">
          <button
            type="submit"
            disabled={!isValid || loading}
            className="flex items-center gap-2 px-6 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading && <Loader2 className="h-4 w-4 animate-spin" />}
            {loading ? 'Creating...' : 'Create Project'}
          </button>
          <Link
            href="/projects"
            className="px-6 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            Cancel
          </Link>
        </div>
      </form>
    </div>
  );
}
