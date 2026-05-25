import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { AppConfig } from '../../../config/configuration';
import { LocalStorageDriver } from './local-storage.driver';
import { S3StorageDriver } from './s3-storage.driver';
import { StorageDriver } from './storage.interface';

/** Selects and exposes the configured storage driver. */
@Injectable()
export class StorageService implements StorageDriver {
  private readonly logger = new Logger(StorageService.name);
  private readonly driver: StorageDriver;

  constructor(private readonly config: ConfigService<AppConfig, true>) {
    const storage = this.config.get('storage', { infer: true });
    if (storage.driver === 's3') {
      this.driver = new S3StorageDriver(storage.s3);
    } else {
      this.driver = new LocalStorageDriver(storage.localPath);
    }
    this.logger.log(`Storage driver: ${this.driver.name}`);
  }

  get name(): string {
    return this.driver.name;
  }

  save(key: string, data: Buffer, mimeType: string): Promise<void> {
    return this.driver.save(key, data, mimeType);
  }

  read(key: string): Promise<Buffer> {
    return this.driver.read(key);
  }

  delete(key: string): Promise<void> {
    return this.driver.delete(key);
  }
}
