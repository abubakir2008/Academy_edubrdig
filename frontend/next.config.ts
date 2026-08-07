import type { NextConfig } from "next";

/**
 * The browser always talks to the same origin (`/api/...`); this rewrite forwards
 * to the Traefik gateway, which strips `/api` and routes by service prefix.
 * In Docker set API_GATEWAY_URL=http://traefik, locally it defaults to :80.
 */
const gateway = process.env.API_GATEWAY_URL ?? "http://localhost";

const nextConfig: NextConfig = {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${gateway}/api/:path*` }];
  },
  images: {
    remotePatterns: [{ protocol: "https", hostname: "**" }],
  },
};

export default nextConfig;
