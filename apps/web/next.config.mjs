/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ['@rawasi/shared-types'],
  eslint: {
    // Lint is run as a separate CI step; don't fail production builds on it.
    ignoreDuringBuilds: true,
  },
};

export default nextConfig;
