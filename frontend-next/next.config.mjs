/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    typedRoutes: false,
  },
  // Ẩn backend URL — proxy mọi /api/v1/* qua Next.js Route Handlers
  async rewrites() {
    return [];
  },
  env: {
    BACKEND_URL: process.env.BACKEND_URL || "http://127.0.0.1:8000",
  },
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "undraw.co" },
      { protocol: "https", hostname: "**" },
    ],
  },
};

export default nextConfig;
