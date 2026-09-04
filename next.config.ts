import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Only use standalone output for Docker container builds, not on Vercel
  ...(process.env.DOCKER_BUILD === "1" ? { output: "standalone" } : {}),
};

export default nextConfig;
