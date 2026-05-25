import { Controller, Get } from '@nestjs/common';
import { ApiBearerAuth, ApiOperation, ApiTags } from '@nestjs/swagger';
import { RequirePermission } from '../../common/decorators/require-permission.decorator';
import { PrismaService } from '../../common/prisma/prisma.service';

@ApiTags('roles')
@ApiBearerAuth()
@Controller('roles')
export class RolesController {
  constructor(private readonly prisma: PrismaService) {}

  @Get()
  @RequirePermission('role', 'read')
  @ApiOperation({ summary: 'قائمة الأدوار' })
  list() {
    return this.prisma.role.findMany({
      select: { id: true, name: true, nameAr: true, description: true, isSystem: true },
      orderBy: { name: 'asc' },
    });
  }
}
