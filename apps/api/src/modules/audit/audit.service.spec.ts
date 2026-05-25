import { AuditService } from './audit.service';

describe('AuditService', () => {
  let prisma: any;
  let service: AuditService;

  beforeEach(() => {
    prisma = { auditLog: { create: jest.fn().mockResolvedValue({}) } };
    service = new AuditService(prisma);
  });

  it('persists an audit entry with mapped fields', async () => {
    await service.record({
      userId: 'u1',
      action: 'CREATE',
      entityType: 'User',
      entityId: 'u2',
      afterState: { email: 'a@b.sa' },
      ip: '127.0.0.1',
      userAgent: 'jest',
    });
    expect(prisma.auditLog.create).toHaveBeenCalledWith(
      expect.objectContaining({
        data: expect.objectContaining({
          userId: 'u1',
          action: 'CREATE',
          entityType: 'User',
          entityId: 'u2',
        }),
      }),
    );
  });

  it('never throws even if the DB write fails', async () => {
    prisma.auditLog.create.mockRejectedValue(new Error('db down'));
    await expect(
      service.record({ action: 'LOGIN', entityType: 'User' }),
    ).resolves.toBeUndefined();
  });
});
