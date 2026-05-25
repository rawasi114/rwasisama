export interface StorageDriver {
  /** Persist bytes under the given key. */
  save(key: string, data: Buffer, mimeType: string): Promise<void>;
  /** Retrieve bytes for the given key. */
  read(key: string): Promise<Buffer>;
  /** Remove the object at the given key (no-op if absent). */
  delete(key: string): Promise<void>;
  /** Driver identifier persisted on the file record. */
  readonly name: string;
}

export const STORAGE_DRIVER = Symbol('STORAGE_DRIVER');
