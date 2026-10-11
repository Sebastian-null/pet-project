import type { NextConfig } from "next";

const publicApi = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
// Inside Docker the API answers on its service name, so image requests made by the
// server (rewrites, the image optimiser) must not go through the browser's URL.
const internalApi = process.env.API_INTERNAL_URL || publicApi;
const mediaOrigin = internalApi.replace(/\/api\/v1\/?$/, "");

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [{ protocol: "https", hostname: "images.unsplash.com", pathname: "/**" }],
  },
  // Product photos and avatars are served from the storefront's own origin and
  // proxied to the API, which keeps them optimisable and CORS-free.
  async rewrites() {
    return [{ source: "/media/:path*", destination: `${mediaOrigin}/media/:path*` }];
  },
  async headers() {
    return [{
      source: "/(.*)",
      headers: [
        { key: "X-Content-Type-Options", value: "nosniff" },
        { key: "X-Frame-Options", value: "SAMEORIGIN" },
        { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
      ],
    }];
  },
};

export default nextConfig;
