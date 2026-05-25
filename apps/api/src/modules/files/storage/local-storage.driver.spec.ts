import { promises as fs } from 'fs';
import * as os from 'os';
import * as path from 'path';
import { LocalStorageDriver } from './local-storage.driver';

describe('LocalStorageDriver', () => {
  let base: string;
  let driver: LocalStorageDriver;

  beforeEach(async () => {
    base = await fs.mkdtemp(path.join(os.tmpdir(), 'rawasi-store-'));
    driver = new LocalStorageDriver(base);
  });

  afterEach(async () => {
    await fs.rm(base, { recursive: true, force: true });
  });

  it('saves and reads bytes round-trip', async () => {
    const data = Buffer.from('مرحبا rawasi', 'utf-8');
    await driver.save('2026/05/file.txt', data, 'text/plain');
    const read = await driver.read('2026/05/file.txt');
    expect(read.equals(data)).toBe(true);
  });

  it('deletes an object (and is a no-op if missing)', async () => {
    await driver.save('a/b.bin', Buffer.from([1, 2, 3]), 'application/octet-stream');
    await driver.delete('a/b.bin');
    await expect(driver.read('a/b.bin')).rejects.toBeDefined();
    await expect(driver.delete('a/b.bin')).resolves.toBeUndefined();
  });

  it('prevents path traversal outside the base directory', async () => {
    await driver.save('../escape.txt', Buffer.from('x'), 'text/plain');
    // File must NOT exist in the parent of base.
    const parentEscape = path.join(path.dirname(base), 'escape.txt');
    await expect(fs.access(parentEscape)).rejects.toBeDefined();
  });
});
