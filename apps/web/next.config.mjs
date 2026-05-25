// عنوان الـ API الداخلي الذي تُمرَّر إليه طلبات "/api/*" (proxy).
// محلياً: http://localhost:4000 — في الإنتاج: يُضبط عبر متغير البيئة API_INTERNAL_URL.
const API_INTERNAL_URL = process.env.API_INTERNAL_URL ?? 'http://localhost:4000';

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // ESLint يُضاف في مرحلة تحسين لاحقة؛ فحص الأنواع يتم عبر tsc + بناء Next.
  eslint: {
    ignoreDuringBuilds: true,
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${API_INTERNAL_URL}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
