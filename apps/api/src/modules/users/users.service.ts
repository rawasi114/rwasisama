import { BadRequestException, ConflictException, Injectable } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { Prisma, User } from '@prisma/client';
import * as bcrypt from 'bcryptjs';
import { AuthContext } from '../../common/decorators/current-user.decorator';
import { AuditService } from '../../common/audit/audit.service';
import { PrismaService } from '../../common/prisma/prisma.service';
import { CreateUserDto } from './dto/create-user.dto';

export interface PublicUser {
  id: string;
  email: string;
  fullNameAr: string;
  fullNameEn: string | null;
  phone: string | null;
  isActive: boolean;
  roleName: string;
  roleNameAr: string;
  createdAt: Date;
}

@Injectable()
export class UsersService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly config: ConfigService,
    private readonly audit: AuditService,
  ) {}

  findByEmail(email: string) {
    return this.prisma.user.findUnique({ where: { email } });
  }

  /** سياق المصادقة (هوية + صلاحيات) المُحمَّل في كل طلب محمي. */
  async findAuthContext(id: string): Promise<AuthContext | null> {
    const user = await this.prisma.user.findUnique({
      where: { id },
      include: { role: { include: { permissions: true } } },
    });
    if (!user) return null;
    return {
      id: user.id,
      email: user.email,
      fullNameAr: user.fullNameAr,
      fullNameEn: user.fullNameEn,
      isActive: user.isActive,
      roleName: user.role.name,
      roleNameAr: user.role.nameAr,
      permissions: user.role.permissions.map((p) => ({ resource: p.resource, action: p.action })),
    };
  }

  async listPublic(): Promise<PublicUser[]> {
    const users = await this.prisma.user.findMany({
      include: { role: true },
      orderBy: { createdAt: 'asc' },
    });
    return users.map((u) => this.toPublic(u, u.role.name, u.role.nameAr));
  }

  async create(dto: CreateUserDto, actorId?: string): Promise<PublicUser> {
    const role = await this.prisma.role.findUnique({ where: { name: dto.roleName } });
    if (!role) throw new BadRequestException(`الدور "${dto.roleName}" غير موجود`);

    const rounds = Number(this.config.get('BCRYPT_SALT_ROUNDS', 12));
    const passwordHash = await bcrypt.hash(dto.password, rounds);

    try {
      const user = await this.prisma.user.create({
        data: {
          email: dto.email,
          passwordHash,
          fullNameAr: dto.fullNameAr,
          fullNameEn: dto.fullNameEn ?? null,
          phone: dto.phone ?? null,
          roleId: role.id,
        },
      });
      await this.audit.log({
        userId: actorId,
        action: 'create',
        resource: 'user',
        resourceId: user.id,
        afterState: { email: user.email, role: role.name },
      });
      return this.toPublic(user, role.name, role.nameAr);
    } catch (err) {
      if (err instanceof Prisma.PrismaClientKnownRequestError && err.code === 'P2002') {
        throw new ConflictException('البريد الإلكتروني مستخدم مسبقاً');
      }
      throw err;
    }
  }

  private toPublic(user: User, roleName: string, roleNameAr: string): PublicUser {
    return {
      id: user.id,
      email: user.email,
      fullNameAr: user.fullNameAr,
      fullNameEn: user.fullNameEn,
      phone: user.phone,
      isActive: user.isActive,
      roleName,
      roleNameAr,
      createdAt: user.createdAt,
    };
  }
}
