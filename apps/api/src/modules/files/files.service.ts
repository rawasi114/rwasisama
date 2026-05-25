import { Injectable, NotFoundException } from '@nestjs/common';
import { createHash, randomUUID } from 'crypto';
import { File as FileRecord } from '@prisma/client';
import { PrismaService } from '../../prisma/prisma.service';
import { StorageService } from './storage/storage.service';

export interface UploadInput {
  originalName: string;
  mimeType: string;
  data: Buffer;
  uploadedById?: string | null;
}

@Injectable()
export class FilesService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly storage: StorageService,
  ) {}

  private buildKey(originalName: string): string {
    const now = new Date();
    const yyyy = now.getUTCFullYear();
    const mm = String(now.getUTCMonth() + 1).padStart(2, '0');
    const ext = originalName.includes('.') ? originalName.split('.').pop() : 'bin';
    return `${yyyy}/${mm}/${randomUUID()}.${ext}`;
  }

  async upload(input: UploadInput): Promise<FileRecord> {
    const storageKey = this.buildKey(input.originalName);
    const checksum = createHash('sha256').update(input.data).digest('hex');

    await this.storage.save(storageKey, input.data, input.mimeType);

    return this.prisma.file.create({
      data: {
        originalName: input.originalName,
        storageKey,
        driver: this.storage.name,
        mimeType: input.mimeType,
        sizeBytes: input.data.length,
        checksum,
        uploadedById: input.uploadedById ?? null,
      },
    });
  }

  async getByIdOrFail(id: string): Promise<FileRecord> {
    const file = await this.prisma.file.findUnique({ where: { id } });
    if (!file) {
      throw new NotFoundException('الملف غير موجود');
    }
    return file;
  }

  async download(id: string): Promise<{ file: FileRecord; data: Buffer }> {
    const file = await this.getByIdOrFail(id);
    const data = await this.storage.read(file.storageKey);
    return { file, data };
  }

  async remove(id: string): Promise<void> {
    const file = await this.getByIdOrFail(id);
    await this.storage.delete(file.storageKey);
    await this.prisma.file.delete({ where: { id } });
  }

  /** Polymorphic link of a file to any entity. */
  async link(fileId: string, entityType: string, entityId: string): Promise<void> {
    await this.getByIdOrFail(fileId);
    await this.prisma.fileLink.upsert({
      where: { fileId_entityType_entityId: { fileId, entityType, entityId } },
      update: {},
      create: { fileId, entityType, entityId },
    });
  }
}
