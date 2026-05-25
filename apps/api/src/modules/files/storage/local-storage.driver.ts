import { promises as fs } from 'fs';
import * as path from 'path';
import { StorageDriver } from './storage.interface';

/** Filesystem-backed storage driver (development / single-node). */
export class LocalStorageDriver implements StorageDriver {
  readonly name = 'local';

  constructor(private readonly basePath: string) {}

  private resolve(key: string): string {
    // Prevent path traversal: keys are relative and normalized under basePath.
    const safeKey = path.normalize(key).replace(/^(\.\.(\/|\\|$))+/, '');
    return path.join(this.basePath, safeKey);
  }

  async save(key: string, data: Buffer, _mimeType?: string): Promise<void> {
    const full = this.resolve(key);
    await fs.mkdir(path.dirname(full), { recursive: true });
    await fs.writeFile(full, data);
  }

  async read(key: string): Promise<Buffer> {
    return fs.readFile(this.resolve(key));
  }

  async delete(key: string): Promise<void> {
    await fs.rm(this.resolve(key), { force: true });
  }
}
