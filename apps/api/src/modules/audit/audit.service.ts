import { Injectable, Logger } from '@nestjs/common';
import { PrismaService } from '../../prisma/prisma.service';

export interface AuditEntry {
  userId?: string | null;
  action: string;
  entityType: string;
  entityId?: string | null;
  beforeState?: unknown;
  afterState?: unknown;
  ip?: string | null;
  userAgent?: string | null;
}

/** Persists audit trail entries for sensitive operations. */
@Injectable()
export class AuditService {
  private readonly logger = new Logger(AuditService.name);

  constructor(private readonly prisma: PrismaService) {}

  async record(entry: AuditEntry): Promise<void> {
    try {
      await this.prisma.auditLog.create({
        data: {
          userId: entry.userId ?? null,
          action: entry.action,
          entityType: entry.entityType,
          entityId: entry.entityId ?? null,
          beforeState: (entry.beforeState ?? undefined) as object | undefined,
          afterState: (entry.afterState ?? undefined) as object | undefined,
          ip: entry.ip ?? null,
          userAgent: entry.userAgent ?? null,
        },
      });
    } catch (err) {
      // Audit must never break the main flow; log and continue.
      this.logger.error(`Failed to record audit entry: ${String(err)}`);
    }
  }
}
