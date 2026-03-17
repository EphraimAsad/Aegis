/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable React strict mode for better development experience
  reactStrictMode: true,

  // Output standalone build for Docker
  output: 'standalone',

  // Environment variables available to the browser
  env: {
    NEXT_PUBLIC_APP_NAME: 'Aegis',
    NEXT_PUBLIC_APP_VERSION: '0.1.0',
  },

  // Rewrites for API proxy (optional, useful for development)
  async rewrites() {
    const apiUrl = process.env.INTERNAL_API_URL || 'http://localhost:8000';
    return [
      {
        source: '/api/backend/:path*',
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
