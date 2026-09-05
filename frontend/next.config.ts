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
  // No remotePatterns: next/image isn't used anywhere in this app yet (plain
  // <img>/<video> throughout). A wildcard hostname here would make Next's
  // image optimizer fetch whatever URL the day someone wires an <Image src>
  // up to user-supplied content (an avatar, CMS media) -- add the specific
  // hostname(s) actually needed at that point instead.
  images: {
    remotePatterns: [],
  },
};

export default nextConfig;
