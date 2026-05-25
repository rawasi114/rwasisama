import { Injectable, UnauthorizedException } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { JwtService } from '@nestjs/jwt';
import * as bcrypt from 'bcryptjs';
import { createHash, randomUUID } from 'node:crypto';
import { AuditService } from '../../common/audit/audit.service';
import { PrismaService } from '../../common/prisma/prisma.service';
import { UsersService } from '../users/users.service';

export interface RequestContext {
  ip?: string | null;
  userAgent?: string | null;
}

const sha256 = (value: string): string => createHash('sha256').update(value).digest('hex');

@Injectable()
export class AuthService {
  private readonly refreshSecret: string;
  private readonly refreshTtl: string;

  constructor(
    private readonly prisma: PrismaService,
    private readonly users: UsersService,
    private readonly jwt: JwtService,
    private readonly config: ConfigService,
    private readonly audit: AuditService,
  ) {
    this.refreshSecret = this.config.getOrThrow<string>('JWT_REFRESH_SECRET');
    this.refreshTtl = this.config.get<string>('JWT_REFRESH_TTL', '7d');
  }

  /** يتحقق من بيانات الدخول ويُرجع معرّف المستخدم. */
  async validateUser(email: string, password: string): Promise<string> {
    const user = await this.users.findByEmail(email);
    if (!user || !user.isActive) throw new UnauthorizedException('بيانات الدخول غير صحيحة');
    const ok = await bcrypt.compare(password, user.passwordHash);
    if (!ok) throw new UnauthorizedException('بيانات الدخول غير صحيحة');
    return user.id;
  }

  async login(userId: string, ctx: RequestContext) {
    const accessToken = await this.jwt.signAsync({ sub: userId });
    const refreshToken = await this.issueRefreshToken(userId, ctx);
    await this.prisma.user.update({ where: { id: userId }, data: { lastLoginAt: new Date() } });
    await this.audit.log({
      userId,
      action: 'login',
      resource: 'auth',
      ip: ctx.ip,
      userAgent: ctx.userAgent,
    });
    const user = await this.users.findAuthContext(userId);
    return { accessToken, refreshToken, user };
  }

  async refresh(token: string, ctx: RequestContext) {
    let payload: { sub: string };
    try {
      payload = await this.jwt.verifyAsync(token, { secret: this.refreshSecret });
    } catch {
      throw new UnauthorizedException('رمز التحديث غير صالح');
    }

    const tokenHash = sha256(token);
    const stored = await this.prisma.refreshToken.findUnique({ where: { tokenHash } });
    if (!stored || stored.revokedAt || stored.expiresAt < new Date()) {
      throw new UnauthorizedException('انتهت صلاحية جلسة التحديث');
    }

    // Rotation: إبطال الرمز القديم وإصدار رمز جديد
    await this.prisma.refreshToken.update({
      where: { id: stored.id },
      data: { revokedAt: new Date() },
    });

    const accessToken = await this.jwt.signAsync({ sub: payload.sub });
    const refreshToken = await this.issueRefreshToken(payload.sub, ctx);
    return { accessToken, refreshToken };
  }

  async logout(token: string) {
    const tokenHash = sha256(token);
    await this.prisma.refreshToken.updateMany({
      where: { tokenHash, revokedAt: null },
      data: { revokedAt: new Date() },
    });
    return { success: true };
  }

  private async issueRefreshToken(userId: string, ctx: RequestContext): Promise<string> {
    const token = await this.jwt.signAsync(
      { sub: userId, jti: randomUUID() },
      { secret: this.refreshSecret, expiresIn: this.refreshTtl },
    );
    const decoded = this.jwt.decode(token) as { exp: number };
    await this.prisma.refreshToken.create({
      data: {
        userId,
        tokenHash: sha256(token),
        expiresAt: new Date(decoded.exp * 1000),
        ip: ctx.ip ?? null,
        userAgent: ctx.userAgent ?? null,
      },
    });
    return token;
  }
}
