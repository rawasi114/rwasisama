import {
  Injectable,
  UnauthorizedException,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { JwtService } from '@nestjs/jwt';
import { createHash } from 'crypto';
import * as bcrypt from 'bcryptjs';
import { AppConfig } from '../../config/configuration';
import { PrismaService } from '../../prisma/prisma.service';
import { AuditService } from '../audit/audit.service';
import { AuthenticatedUser } from '../../common/types/authenticated-user';

export interface RequestContext {
  ip?: string | null;
  userAgent?: string | null;
}

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
}

const userInclude = {
  role: { include: { permissions: { include: { permission: true } } } },
} as const;

@Injectable()
export class AuthService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly jwt: JwtService,
    private readonly config: ConfigService<AppConfig, true>,
    private readonly audit: AuditService,
  ) {}

  private hashToken(token: string): string {
    return createHash('sha256').update(token).digest('hex');
  }

  private toAuthUser(user: {
    id: string;
    email: string;
    fullNameAr: string;
    fullNameEn: string | null;
    role: {
      id: string;
      key: string;
      nameAr: string;
      nameEn: string;
      permissions: { permission: { action: string; subject: string } }[];
    };
  }): AuthenticatedUser {
    return {
      id: user.id,
      email: user.email,
      fullNameAr: user.fullNameAr,
      fullNameEn: user.fullNameEn,
      role: {
        id: user.role.id,
        key: user.role.key,
        nameAr: user.role.nameAr,
        nameEn: user.role.nameEn,
      },
      permissions: user.role.permissions.map((rp) => ({
        action: rp.permission.action,
        subject: rp.permission.subject,
      })),
    };
  }

  /** Used by JwtStrategy to load the user on every authenticated request. */
  async loadAuthenticatedUser(userId: string): Promise<AuthenticatedUser | null> {
    const user = await this.prisma.user.findUnique({
      where: { id: userId },
      include: userInclude,
    });
    if (!user || !user.isActive) {
      return null;
    }
    return this.toAuthUser(user);
  }

  async validateCredentials(
    email: string,
    password: string,
  ): Promise<AuthenticatedUser | null> {
    const user = await this.prisma.user.findUnique({
      where: { email },
      include: userInclude,
    });
    if (!user || !user.isActive) {
      return null;
    }
    const ok = await bcrypt.compare(password, user.passwordHash);
    if (!ok) {
      return null;
    }
    return this.toAuthUser(user);
  }

  private async issueTokens(userId: string, ctx: RequestContext): Promise<AuthTokens> {
    const jwtCfg = this.config.get('jwt', { infer: true });

    const accessToken = await this.jwt.signAsync(
      { sub: userId },
      { secret: jwtCfg.accessSecret, expiresIn: jwtCfg.accessTtl },
    );
    const refreshToken = await this.jwt.signAsync(
      { sub: userId },
      { secret: jwtCfg.refreshSecret, expiresIn: jwtCfg.refreshTtl },
    );

    const decoded = this.jwt.decode(refreshToken) as { exp: number };
    await this.prisma.refreshToken.create({
      data: {
        userId,
        tokenHash: this.hashToken(refreshToken),
        expiresAt: new Date(decoded.exp * 1000),
        ip: ctx.ip ?? null,
        userAgent: ctx.userAgent ?? null,
      },
    });

    return { accessToken, refreshToken };
  }

  async login(
    email: string,
    password: string,
    ctx: RequestContext,
  ): Promise<{ user: AuthenticatedUser; tokens: AuthTokens }> {
    const user = await this.validateCredentials(email, password);
    if (!user) {
      throw new UnauthorizedException('بيانات الدخول غير صحيحة');
    }

    const tokens = await this.issueTokens(user.id, ctx);
    await this.prisma.user.update({
      where: { id: user.id },
      data: { lastLoginAt: new Date() },
    });
    await this.audit.record({
      userId: user.id,
      action: 'LOGIN',
      entityType: 'User',
      entityId: user.id,
      ip: ctx.ip,
      userAgent: ctx.userAgent,
    });

    return { user, tokens };
  }

  /** Verifies, revokes (rotates), and re-issues a token pair. */
  async refresh(refreshToken: string, ctx: RequestContext): Promise<AuthTokens> {
    const jwtCfg = this.config.get('jwt', { infer: true });
    let payload: { sub: string };
    try {
      payload = await this.jwt.verifyAsync(refreshToken, {
        secret: jwtCfg.refreshSecret,
      });
    } catch {
      throw new UnauthorizedException('رمز التحديث غير صالح');
    }

    const tokenHash = this.hashToken(refreshToken);
    const stored = await this.prisma.refreshToken.findUnique({ where: { tokenHash } });
    if (!stored || stored.revokedAt || stored.expiresAt < new Date()) {
      throw new UnauthorizedException('انتهت صلاحية الجلسة، يرجى تسجيل الدخول مجدداً');
    }

    // Rotate: revoke the used token, issue a fresh pair.
    await this.prisma.refreshToken.update({
      where: { id: stored.id },
      data: { revokedAt: new Date() },
    });

    return this.issueTokens(payload.sub, ctx);
  }

  async logout(refreshToken: string): Promise<void> {
    const tokenHash = this.hashToken(refreshToken);
    await this.prisma.refreshToken.updateMany({
      where: { tokenHash, revokedAt: null },
      data: { revokedAt: new Date() },
    });
  }
}
