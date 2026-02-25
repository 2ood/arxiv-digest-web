/** @type {import('next').NextConfig} */
const nextConfig = {
  // Digest calls can take up to 60s (embedding model)
  experimental: {
    serverActions: { bodySizeLimit: "2mb" },
  },
};

module.exports = nextConfig;
