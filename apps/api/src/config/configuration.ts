/** Structured, typed application configuration loaded from environment. */
export interface AppConfig {
  nodeEnv: string;
  api: { port: number; globalPrefix: string };
  jwt: {
    accessSecret: string;
    accessTtl: string;
    refreshSecret: string;
    refreshTtl: string;
  };
  bcryptCost: number;
  rateLimit: { ttl: number; max: number };
  storage: {
    driver: 'local' | 's3';
    localPath: string;
    s3: {
      endpoint: string;
      region: string;
      bucket: string;
      accessKey: string;
      secretKey: string;
      forcePathStyle: boolean;
    };
  };
}

export default (): AppConfig => ({
  nodeEnv: process.env.NODE_ENV ?? 'development',
  api: {
    port: Number(process.env.API_PORT ?? 4000),
    globalPrefix: process.env.API_GLOBAL_PREFIX ?? 'api',
  },
  jwt: {
    accessSecret: process.env.JWT_ACCESS_SECRET ?? 'dev_access_secret',
    accessTtl: process.env.JWT_ACCESS_TTL ?? '15m',
    refreshSecret: process.env.JWT_REFRESH_SECRET ?? 'dev_refresh_secret',
    refreshTtl: process.env.JWT_REFRESH_TTL ?? '7d',
  },
  bcryptCost: Number(process.env.BCRYPT_COST ?? 12),
  rateLimit: {
    ttl: Number(process.env.RATE_LIMIT_TTL ?? 60),
    max: Number(process.env.RATE_LIMIT_MAX ?? 100),
  },
  storage: {
    driver: (process.env.STORAGE_DRIVER as 'local' | 's3') ?? 'local',
    localPath: process.env.STORAGE_LOCAL_PATH ?? './storage',
    s3: {
      endpoint: process.env.S3_ENDPOINT ?? '',
      region: process.env.S3_REGION ?? 'us-east-1',
      bucket: process.env.S3_BUCKET ?? 'rawasi-files',
      accessKey: process.env.S3_ACCESS_KEY ?? '',
      secretKey: process.env.S3_SECRET_KEY ?? '',
      forcePathStyle: (process.env.S3_FORCE_PATH_STYLE ?? 'true') === 'true',
    },
  },
});
