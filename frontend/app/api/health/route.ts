import { NextResponse } from 'next/server';

export async function GET() {
  const apiUrl = process.env.INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  try {
    // Check backend health
    const backendResponse = await fetch(`${apiUrl}/api/v1/health`, {
      cache: 'no-store',
    });

    const backendHealth = backendResponse.ok ? await backendResponse.json() : null;

    return NextResponse.json({
      status: 'ok',
      frontend: {
        status: 'healthy',
        version: process.env.NEXT_PUBLIC_APP_VERSION || '0.1.0',
      },
      backend: backendHealth ? {
        status: backendHealth.status,
        version: backendHealth.version,
        database: backendHealth.database,
        redis: backendHealth.redis,
      } : {
        status: 'unhealthy',
        error: 'Backend unavailable',
      },
    });
  } catch (error) {
    return NextResponse.json({
      status: 'degraded',
      frontend: {
        status: 'healthy',
        version: process.env.NEXT_PUBLIC_APP_VERSION || '0.1.0',
      },
      backend: {
        status: 'unhealthy',
        error: error instanceof Error ? error.message : 'Unknown error',
      },
    });
  }
}
