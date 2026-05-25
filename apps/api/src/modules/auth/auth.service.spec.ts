import { UnauthorizedException } from '@nestjs/common';
import * as bcrypt from 'bcryptjs';
import { AuthService } from './auth.service';

const JWT_CFG = {
  accessSecret: 'a',
  accessTtl: '15m',
  refreshSecret: 'r',
  refreshTtl: '7d',
};

function buildUserRecord(passwordHash: string, isActive = true) {
  return {
    id: 'u1',
    email: 'admin@rawasi-sama.sa',
    passwordHash,
    fullNameAr: 'مدير',
    fullNameEn: 'Admin',
    isActive,
    role: {
      id: 'r1',
      key: 'CEO',
      nameAr: 'المدير العام',
      nameEn: 'CEO',
      permissions: [{ permission: { action: 'manage', subject: 'all' } }],
    },
  };
}

describe('AuthService', () => {
  let prisma: any;
  let jwt: any;
  let config: any;
  let audit: any;
  let service: AuthService;
  let passwordHash: string;

  beforeAll(async () => {
    passwordHash = await bcrypt.hash('Admin@12345', 8);
  });

  beforeEach(() => {
    prisma = {
      user: { findUnique: jest.fn(), update: jest.fn().mockResolvedValue({}) },
      refreshToken: {
        create: jest.fn().mockResolvedValue({}),
        findUnique: jest.fn(),
        update: jest.fn().mockResolvedValue({}),
        updateMany: jest.fn().mockResolvedValue({ count: 1 }),
      },
    };
    jwt = {
      signAsync: jest
        .fn()
        .mockResolvedValueOnce('access.jwt')
        .mockResolvedValueOnce('refresh.jwt'),
      verifyAsync: jest.fn(),
      decode: jest.fn().mockReturnValue({ exp: Math.floor(Date.now() / 1000) + 3600 }),
    };
    config = { get: jest.fn().mockReturnValue(JWT_CFG) };
    audit = { record: jest.fn().mockResolvedValue(undefined) };
    service = new AuthService(prisma, jwt, config, audit);
  });

  describe('validateCredentials', () => {
    it('returns the auth user for valid credentials', async () => {
      prisma.user.findUnique.mockResolvedValue(buildUserRecord(passwordHash));
      const user = await service.validateCredentials('admin@rawasi-sama.sa', 'Admin@12345');
      expect(user).not.toBeNull();
      expect(user!.permissions).toEqual([{ action: 'manage', subject: 'all' }]);
    });

    it('returns null for a wrong password', async () => {
      prisma.user.findUnique.mockResolvedValue(buildUserRecord(passwordHash));
      expect(await service.validateCredentials('admin@rawasi-sama.sa', 'wrong')).toBeNull();
    });

    it('returns null for an inactive user', async () => {
      prisma.user.findUnique.mockResolvedValue(buildUserRecord(passwordHash, false));
      expect(await service.validateCredentials('admin@rawasi-sama.sa', 'Admin@12345')).toBeNull();
    });

    it('returns null for an unknown email', async () => {
      prisma.user.findUnique.mockResolvedValue(null);
      expect(await service.validateCredentials('nobody@x.sa', 'whatever12')).toBeNull();
    });
  });

  describe('login', () => {
    it('issues tokens, stores refresh hash, updates lastLogin, and audits', async () => {
      prisma.user.findUnique.mockResolvedValue(buildUserRecord(passwordHash));
      const { user, tokens } = await service.login('admin@rawasi-sama.sa', 'Admin@12345', {
        ip: '127.0.0.1',
        userAgent: 'jest',
      });
      expect(tokens.accessToken).toBe('access.jwt');
      expect(tokens.refreshToken).toBe('refresh.jwt');
      expect(prisma.refreshToken.create).toHaveBeenCalledTimes(1);
      expect(prisma.user.update).toHaveBeenCalledWith(
        expect.objectContaining({ where: { id: user.id } }),
      );
      expect(audit.record).toHaveBeenCalledWith(
        expect.objectContaining({ action: 'LOGIN', userId: 'u1' }),
      );
    });

    it('throws Unauthorized for bad credentials', async () => {
      prisma.user.findUnique.mockResolvedValue(null);
      await expect(
        service.login('x@y.sa', 'bad-password', {}),
      ).rejects.toBeInstanceOf(UnauthorizedException);
    });
  });

  describe('refresh', () => {
    it('rotates a valid refresh token', async () => {
      jwt.verifyAsync.mockResolvedValue({ sub: 'u1' });
      prisma.refreshToken.findUnique.mockResolvedValue({
        id: 'rt1',
        revokedAt: null,
        expiresAt: new Date(Date.now() + 3600_000),
      });
      const tokens = await service.refresh('refresh.jwt', {});
      expect(prisma.refreshToken.update).toHaveBeenCalledWith(
        expect.objectContaining({ where: { id: 'rt1' } }),
      );
      expect(tokens.accessToken).toBe('access.jwt');
    });

    it('rejects a revoked refresh token', async () => {
      jwt.verifyAsync.mockResolvedValue({ sub: 'u1' });
      prisma.refreshToken.findUnique.mockResolvedValue({
        id: 'rt1',
        revokedAt: new Date(),
        expiresAt: new Date(Date.now() + 3600_000),
      });
      await expect(service.refresh('refresh.jwt', {})).rejects.toBeInstanceOf(
        UnauthorizedException,
      );
    });

    it('rejects an invalid (unverifiable) token', async () => {
      jwt.verifyAsync.mockRejectedValue(new Error('bad signature'));
      await expect(service.refresh('tampered', {})).rejects.toBeInstanceOf(
        UnauthorizedException,
      );
    });
  });

  describe('logout', () => {
    it('revokes the matching refresh token', async () => {
      await service.logout('refresh.jwt');
      expect(prisma.refreshToken.updateMany).toHaveBeenCalledWith(
        expect.objectContaining({ data: { revokedAt: expect.any(Date) } }),
      );
    });
  });
});
