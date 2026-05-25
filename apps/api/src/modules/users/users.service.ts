import { ConflictException, Injectable, NotFoundException } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import * as bcrypt from 'bcryptjs';
import { AppConfig } from '../../config/configuration';
import { PrismaService } from '../../prisma/prisma.service';
import { CreateUserDto } from './dto/create-user.dto';

const publicSelect = {
  id: true,
  email: true,
  fullNameAr: true,
  fullNameEn: true,
  phone: true,
  isActive: true,
  lastLoginAt: true,
  createdAt: true,
  role: { select: { id: true, key: true, nameAr: true, nameEn: true } },
} as const;

@Injectable()
export class UsersService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly config: ConfigService<AppConfig, true>,
  ) {}

  findAll() {
    return this.prisma.user.findMany({
      select: publicSelect,
      orderBy: { createdAt: 'desc' },
    });
  }

  async findById(id: string) {
    const user = await this.prisma.user.findUnique({
      where: { id },
      select: publicSelect,
    });
    if (!user) {
      throw new NotFoundException('المستخدم غير موجود');
    }
    return user;
  }

  async create(dto: CreateUserDto) {
    const existing = await this.prisma.user.findUnique({ where: { email: dto.email } });
    if (existing) {
      throw new ConflictException('البريد الإلكتروني مستخدم مسبقاً');
    }
    const role = await this.prisma.role.findUnique({ where: { id: dto.roleId } });
    if (!role) {
      throw new NotFoundException('الدور المحدد غير موجود');
    }

    const cost = this.config.get('bcryptCost', { infer: true });
    const passwordHash = await bcrypt.hash(dto.password, cost);

    return this.prisma.user.create({
      data: {
        email: dto.email,
        passwordHash,
        fullNameAr: dto.fullNameAr,
        fullNameEn: dto.fullNameEn ?? null,
        phone: dto.phone ?? null,
        roleId: dto.roleId,
      },
      select: publicSelect,
    });
  }
}
