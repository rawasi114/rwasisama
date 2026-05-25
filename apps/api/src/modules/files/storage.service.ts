import { Injectable, NotImplementedException } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, isAbsolute, join, resolve } from 'node:path';

/**
 * تجريد تخزين الملفات. السائق الافتراضي "local" (قرص محلي للتطوير).
 * سائق "s3" (متوافق مع MinIO/S3) سيُضاف في مرحلة لاحقة.
 */
@Injectable()
export class StorageService {
  private readonly driver: string;
  private readonly localBase: string;

  constructor(config: ConfigService) {
    this.driver = config.get<string>('STORAGE_DRIVER', 'local');
    const configured = config.get<string>('STORAGE_LOCAL_PATH', './.localstorage');
    this.localBase = isAbsolute(configured) ? configured : resolve(process.cwd(), configured);
  }

  get driverName(): string {
    return this.driver;
  }

  async put(key: string, data: Buffer): Promise<void> {
    if (this.driver !== 'local') {
      throw new NotImplementedException('سائق التخزين S3 لم يُفعّل بعد (مرحلة لاحقة)');
    }
    const full = join(this.localBase, key);
    await mkdir(dirname(full), { recursive: true });
    await writeFile(full, data);
  }

  async get(key: string): Promise<Buffer> {
    if (this.driver !== 'local') {
      throw new NotImplementedException('سائق التخزين S3 لم يُفعّل بعد (مرحلة لاحقة)');
    }
    return readFile(join(this.localBase, key));
  }
}
