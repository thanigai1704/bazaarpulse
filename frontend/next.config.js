/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    // Dev convenience: proxies /api and /ws to the local FastAPI backend.
    const apiHost = process.env.BACKEND_URL || "http://localhost:8000";
    return [
      { source: "/api/:path*", destination: `${apiHost}/:path*` },
    ];
  },
};

module.exports = nextConfig;
