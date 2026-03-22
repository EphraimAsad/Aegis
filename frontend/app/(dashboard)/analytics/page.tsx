'use client';

import { Suspense, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import {
  BarChart3,
  Loader2,
  AlertCircle,
  TrendingUp,
  Users,
  Tag,
  FileText,
} from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import type { AnalyticsOverview } from '@/types/api';

function AnalyticsPageContent() {
  const searchParams = useSearchParams();
  const projectId = searchParams.get('project_id');

  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [trends, setTrends] = useState<Record<number, number>>({});
  const [authors, setAuthors] = useState<{ name: string; count: number }[]>([]);
  const [keywords, setKeywords] = useState<{ keyword: string; count: number }[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) {
      setLoading(false);
      return;
    }

    async function fetchAnalytics() {
      try {
        const [overviewData, trendsData, authorsData, keywordsData] = await Promise.all([
          apiClient.getAnalyticsOverview(Number(projectId)),
          apiClient.getPublicationTrends(Number(projectId)),
          apiClient.getTopAuthors(Number(projectId)),
          apiClient.getKeywordAnalysis(Number(projectId)),
        ]);
        setOverview(overviewData);
        setTrends(trendsData);
        setAuthors(authorsData);
        setKeywords(keywordsData);
      } catch (err) {
        setError('Failed to load analytics');
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    fetchAnalytics();
  }, [projectId]);

  if (!projectId) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Analytics</h1>
          <p className="text-muted-foreground">
            Select a project to view analytics
          </p>
        </div>
        <div className="flex flex-col items-center justify-center h-64 border rounded-lg bg-muted/30">
          <BarChart3 className="h-12 w-12 text-muted-foreground mb-4" />
          <p className="text-muted-foreground">
            Go to a project and click Analytics to view insights
          </p>
        </div>
      </div>
    );
  }

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

  const sortedYears = Object.entries(trends).sort(([a], [b]) => Number(a) - Number(b));
  const maxCount = Math.max(...Object.values(trends), 1);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Analytics</h1>
        <p className="text-muted-foreground">
          Insights for project #{projectId}
        </p>
      </div>

      {/* Overview Stats */}
      {overview && (
        <div className="grid gap-4 sm:grid-cols-4">
          <div className="border rounded-lg p-4">
            <div className="flex items-center gap-2 text-muted-foreground mb-1">
              <FileText className="h-4 w-4" />
              <span className="text-sm">Total Documents</span>
            </div>
            <p className="text-2xl font-bold">{overview.total_documents}</p>
          </div>
          <div className="border rounded-lg p-4">
            <div className="flex items-center gap-2 text-muted-foreground mb-1">
              <TrendingUp className="h-4 w-4" />
              <span className="text-sm">Total Citations</span>
            </div>
            <p className="text-2xl font-bold">{overview.total_citations}</p>
          </div>
          <div className="border rounded-lg p-4">
            <div className="flex items-center gap-2 text-muted-foreground mb-1">
              <BarChart3 className="h-4 w-4" />
              <span className="text-sm">Avg Citations</span>
            </div>
            <p className="text-2xl font-bold">{overview.avg_citations.toFixed(1)}</p>
          </div>
          <div className="border rounded-lg p-4">
            <div className="flex items-center gap-2 text-muted-foreground mb-1">
              <span className="text-sm">Open Access</span>
            </div>
            <p className="text-2xl font-bold">{overview.open_access_count}</p>
          </div>
        </div>
      )}

      {/* Publication Trends */}
      <div className="border rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <TrendingUp className="h-5 w-5" />
          Publication Trends
        </h2>
        {sortedYears.length > 0 ? (
          <div className="space-y-2">
            {sortedYears.map(([year, count]) => (
              <div key={year} className="flex items-center gap-4">
                <span className="w-12 text-sm text-muted-foreground">{year}</span>
                <div className="flex-1 h-6 bg-muted rounded overflow-hidden">
                  <div
                    className="h-full bg-primary transition-all"
                    style={{ width: `${(count / maxCount) * 100}%` }}
                  />
                </div>
                <span className="w-12 text-sm text-right">{count}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-muted-foreground text-center py-8">No publication data</p>
        )}
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Top Authors */}
        <div className="border rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Users className="h-5 w-5" />
            Top Authors
          </h2>
          {authors.length > 0 ? (
            <ul className="space-y-2">
              {authors.slice(0, 10).map((author, index) => (
                <li key={index} className="flex items-center justify-between py-1">
                  <span className="text-sm truncate">{author.name}</span>
                  <span className="text-sm text-muted-foreground">{author.count} papers</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-muted-foreground text-center py-8">No author data</p>
          )}
        </div>

        {/* Keywords */}
        <div className="border rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Tag className="h-5 w-5" />
            Top Keywords
          </h2>
          {keywords.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {keywords.slice(0, 20).map((kw, index) => (
                <span
                  key={index}
                  className="px-2 py-1 bg-muted rounded text-sm"
                  title={`${kw.count} occurrences`}
                >
                  {kw.keyword}
                </span>
              ))}
            </div>
          ) : (
            <p className="text-muted-foreground text-center py-8">No keyword data</p>
          )}
        </div>
      </div>
    </div>
  );
}

export default function AnalyticsPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    }>
      <AnalyticsPageContent />
    </Suspense>
  );
}
