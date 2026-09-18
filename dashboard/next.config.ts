import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async redirects() {
    return [
      {
        source: "/evidence",
        destination: "/?tab=evidence",
        permanent: true,
      },
      {
        source: "/debate",
        destination: "/?tab=debate",
        permanent: true,
      },
      {
        source: "/baseline",
        destination: "/?tab=baseline",
        permanent: true,
      },
      {
        source: "/sonar-live",
        destination: "/?tab=sonar-live",
        permanent: true,
      },
      {
        source: "/history",
        destination: "/?tab=history",
        permanent: true,
      },
      {
        source: "/settings",
        destination: "/?tab=settings",
        permanent: true,
      },
    ];
  },
};

export default nextConfig;