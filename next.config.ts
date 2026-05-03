import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // In dev, proxy /api/* to the local Python server.
  // On Vercel, api/*.py serverless functions handle these routes natively.
  async rewrites() {
    if (process.env.NODE_ENV !== "development") return [];
    return [
      { source: "/api/:path*", destination: "http://127.0.0.1:8000/api/:path*" },
    ];
  },
};

export default nextConfig;
