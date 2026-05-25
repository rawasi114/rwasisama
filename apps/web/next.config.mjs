/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // ESLint يُضاف في مرحلة تحسين لاحقة؛ فحص الأنواع يتم عبر tsc + بناء Next.
  eslint: {
    ignoreDuringBuilds: true,
  },
};

export default nextConfig;
