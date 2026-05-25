/**
 * Minimal env validation. In production the JWT secrets must be set and must
 * not be the development defaults; throws on boot if violated.
 */
export function validateEnv(env: Record<string, unknown>): Record<string, unknown> {
  const isProd = env.NODE_ENV === 'production';

  const required = ['DATABASE_URL'];
  const missing = required.filter((k) => !env[k]);
  if (missing.length > 0) {
    throw new Error(`Missing required environment variables: ${missing.join(', ')}`);
  }

  if (isProd) {
    const weak = ['dev_access_secret', 'dev_refresh_secret', undefined, ''];
    if (weak.includes(env.JWT_ACCESS_SECRET as string)) {
      throw new Error('JWT_ACCESS_SECRET must be set to a strong value in production');
    }
    if (weak.includes(env.JWT_REFRESH_SECRET as string)) {
      throw new Error('JWT_REFRESH_SECRET must be set to a strong value in production');
    }
  }

  return env;
}
