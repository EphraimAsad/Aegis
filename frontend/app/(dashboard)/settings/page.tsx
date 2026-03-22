'use client';

import { useEffect, useState } from 'react';
import { Settings, Server, Loader2, CheckCircle, XCircle, RefreshCw } from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import type { Provider } from '@/types/api';

export default function SettingsPage() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [healthStatus, setHealthStatus] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchProviders = async () => {
    try {
      const [providersData, healthData] = await Promise.all([
        apiClient.getProviders(),
        apiClient.checkProvidersHealth(),
      ]);
      setProviders(providersData);
      setHealthStatus(healthData);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchProviders();
  }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchProviders();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-muted-foreground">
          Configure providers and application settings
        </p>
      </div>

      {/* Providers Section */}
      <div className="border rounded-lg p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Server className="h-5 w-5" />
            AI Providers
          </h2>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-2 px-3 py-1.5 text-sm border rounded-md hover:bg-muted transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        <div className="space-y-4">
          {providers.map((provider) => (
            <div
              key={provider.name}
              className="flex items-center justify-between p-4 border rounded-md"
            >
              <div className="flex items-center gap-4">
                <div className={`w-2 h-2 rounded-full ${
                  healthStatus[provider.name] ? 'bg-green-500' : 'bg-red-500'
                }`} />
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium capitalize">{provider.name}</span>
                    {provider.is_default && (
                      <span className="px-2 py-0.5 bg-primary/10 text-primary text-xs rounded">
                        Default
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {provider.is_healthy ? 'Connected' : 'Not connected'}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                {healthStatus[provider.name] ? (
                  <CheckCircle className="h-5 w-5 text-green-500" />
                ) : (
                  <XCircle className="h-5 w-5 text-red-500" />
                )}
              </div>
            </div>
          ))}
        </div>

        {providers.length === 0 && (
          <p className="text-center text-muted-foreground py-8">
            No providers configured. Make sure Ollama is running or configure API keys.
          </p>
        )}
      </div>

      {/* Capabilities */}
      <div className="border rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4">Provider Capabilities</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b">
                <th className="text-left py-2 px-3">Provider</th>
                <th className="text-center py-2 px-3">Chat</th>
                <th className="text-center py-2 px-3">Completion</th>
                <th className="text-center py-2 px-3">Embeddings</th>
                <th className="text-center py-2 px-3">Streaming</th>
              </tr>
            </thead>
            <tbody>
              {providers.map((provider) => (
                <tr key={provider.name} className="border-b last:border-0">
                  <td className="py-2 px-3 font-medium capitalize">{provider.name}</td>
                  <td className="text-center py-2 px-3">
                    {provider.capabilities.supports_chat ? (
                      <CheckCircle className="h-4 w-4 text-green-500 inline" />
                    ) : (
                      <XCircle className="h-4 w-4 text-muted-foreground inline" />
                    )}
                  </td>
                  <td className="text-center py-2 px-3">
                    {provider.capabilities.supports_completion ? (
                      <CheckCircle className="h-4 w-4 text-green-500 inline" />
                    ) : (
                      <XCircle className="h-4 w-4 text-muted-foreground inline" />
                    )}
                  </td>
                  <td className="text-center py-2 px-3">
                    {provider.capabilities.supports_embeddings ? (
                      <CheckCircle className="h-4 w-4 text-green-500 inline" />
                    ) : (
                      <XCircle className="h-4 w-4 text-muted-foreground inline" />
                    )}
                  </td>
                  <td className="text-center py-2 px-3">
                    {provider.capabilities.supports_streaming ? (
                      <CheckCircle className="h-4 w-4 text-green-500 inline" />
                    ) : (
                      <XCircle className="h-4 w-4 text-muted-foreground inline" />
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Environment Info */}
      <div className="border rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4">Environment</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <p className="text-sm text-muted-foreground">API URL</p>
            <p className="font-mono text-sm">
              {process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}
            </p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Frontend Version</p>
            <p className="font-mono text-sm">0.1.0</p>
          </div>
        </div>
      </div>
    </div>
  );
}
