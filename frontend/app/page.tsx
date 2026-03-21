'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { BookOpen, Database, Server, Cpu, ArrowRight } from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import type { HealthResponse } from '@/types/api';

type HealthStatus = 'loading' | 'healthy' | 'degraded' | 'error';

export default function Home() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [status, setStatus] = useState<HealthStatus>('loading');

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await apiClient.health();
        setHealth(response);
        setStatus(response.status === 'healthy' ? 'healthy' : 'degraded');
      } catch (error) {
        console.error('Health check failed:', error);
        setStatus('error');
      }
    };

    checkHealth();
    // Check every 30 seconds
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (s: HealthStatus | string) => {
    switch (s) {
      case 'healthy':
        return 'bg-green-500';
      case 'degraded':
        return 'bg-yellow-500';
      case 'loading':
        return 'bg-gray-400 animate-pulse';
      default:
        return 'bg-red-500';
    }
  };

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <div className="max-w-4xl w-full space-y-12">
        {/* Header */}
        <div className="text-center space-y-4">
          <div className="flex items-center justify-center gap-3">
            <BookOpen className="h-12 w-12 text-primary" />
            <h1 className="text-5xl font-bold tracking-tight">Aegis</h1>
          </div>
          <p className="text-xl text-muted-foreground">
            Research-focused agentic AI wrapper for academia
          </p>
        </div>

        {/* Status Card */}
        <div className="rounded-lg border bg-card p-6 shadow-sm">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold">System Status</h2>
            <div className="flex items-center gap-2">
              <div className={`h-3 w-3 rounded-full ${getStatusColor(status)}`} />
              <span className="text-sm capitalize">{status}</span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Backend Status */}
            <div className="flex items-center gap-3 p-4 rounded-md bg-muted/50">
              <Server className="h-5 w-5 text-muted-foreground" />
              <div>
                <p className="text-sm font-medium">Backend</p>
                <div className="flex items-center gap-2">
                  <div
                    className={`h-2 w-2 rounded-full ${getStatusColor(
                      status === 'loading' ? 'loading' : status === 'error' ? 'error' : 'healthy'
                    )}`}
                  />
                  <span className="text-xs text-muted-foreground">
                    {health?.version ? `v${health.version}` : 'Checking...'}
                  </span>
                </div>
              </div>
            </div>

            {/* Database Status */}
            <div className="flex items-center gap-3 p-4 rounded-md bg-muted/50">
              <Database className="h-5 w-5 text-muted-foreground" />
              <div>
                <p className="text-sm font-medium">Database</p>
                <div className="flex items-center gap-2">
                  <div
                    className={`h-2 w-2 rounded-full ${getStatusColor(
                      status === 'loading' ? 'loading' : health?.database || 'error'
                    )}`}
                  />
                  <span className="text-xs text-muted-foreground capitalize">
                    {health?.database || 'Checking...'}
                  </span>
                </div>
              </div>
            </div>

            {/* Redis Status */}
            <div className="flex items-center gap-3 p-4 rounded-md bg-muted/50">
              <Cpu className="h-5 w-5 text-muted-foreground" />
              <div>
                <p className="text-sm font-medium">Redis</p>
                <div className="flex items-center gap-2">
                  <div
                    className={`h-2 w-2 rounded-full ${getStatusColor(
                      status === 'loading' ? 'loading' : health?.redis || 'error'
                    )}`}
                  />
                  <span className="text-xs text-muted-foreground capitalize">
                    {health?.redis || 'Checking...'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Features Preview */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="rounded-lg border p-6 space-y-2">
            <h3 className="font-semibold">Multi-Provider Support</h3>
            <p className="text-sm text-muted-foreground">
              Use Ollama locally, or connect to OpenAI, Anthropic, and more.
            </p>
          </div>
          <div className="rounded-lg border p-6 space-y-2">
            <h3 className="font-semibold">Academic Sources</h3>
            <p className="text-sm text-muted-foreground">
              Search OpenAlex, Crossref, Semantic Scholar, arXiv, and PubMed.
            </p>
          </div>
          <div className="rounded-lg border p-6 space-y-2">
            <h3 className="font-semibold">Long-Running Jobs</h3>
            <p className="text-sm text-muted-foreground">
              Run comprehensive research tasks overnight with progress tracking.
            </p>
          </div>
          <div className="rounded-lg border p-6 space-y-2">
            <h3 className="font-semibold">Smart Organization</h3>
            <p className="text-sm text-muted-foreground">
              Automatic chunking, embeddings, summaries, and evidence extraction.
            </p>
          </div>
        </div>

        {/* CTA */}
        <div className="flex justify-center gap-4">
          <Link
            href="/projects"
            className="flex items-center gap-2 px-6 py-3 bg-primary text-primary-foreground rounded-md font-medium hover:bg-primary/90 transition-colors"
          >
            Get Started
            <ArrowRight className="h-4 w-4" />
          </Link>
          <Link
            href="/search"
            className="flex items-center gap-2 px-6 py-3 border rounded-md font-medium hover:bg-muted transition-colors"
          >
            Search Papers
          </Link>
        </div>

        {/* Footer */}
        <div className="text-center text-sm text-muted-foreground">
          <p>Aegis v0.1.0 - Phase 8: Polish & Testing</p>
        </div>
      </div>
    </main>
  );
}
