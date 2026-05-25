import { Injectable, NotFoundException } from '@nestjs/common';
import { File } from '@prisma/client';
import { createHash, randomUUID } from 'node:crypto';
import { extname } from 'node:path';
import { PrismaService } from '../../common/prisma/prisma.service';
import { StorageService } from './storage.service';

@Injectable()
export class FilesService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly storage: StorageService,
  ) {}

  async upload(file: Express.Multer.File, userId?: string): Promise<File> {
    const ext = extname(file.originalname);
    const key = `${new Date().getFullYear()}/${randomUUID()}${ext}`;
    await this.storage.put(key, file.buffer);
    const checksum = createHash('sha256').update(file.buffer).digest('hex');

    return this.prisma.file.create({
      data: {
        originalName: file.originalname,
        storageKey: key,
        driver: this.storage.driverName,
        mimeType: file.mimetype,
        sizeBytes: file.size,
        checksum,
        uploadedById: userId ?? null,
      },
    });
  }

  async getMeta(id: string): Promise<File> {
    const file = await this.prisma.file.findUnique({ where: { id } });
    if (!file) throw new NotFoundException('الملف غير موجود');
    return file;
  }

  async download(id: string): Promise<{ meta: File; buffer: Buffer }> {
    const meta = await this.getMeta(id);
    const buffer = await this.storage.get(meta.storageKey);
    return { meta, buffer };
  }
}
