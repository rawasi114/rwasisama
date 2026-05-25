import { CanActivate, ExecutionContext, ForbiddenException, Injectable } from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { AuthContext } from '../decorators/current-user.decorator';
import { PERMISSION_KEY, RequiredPermission } from '../decorators/require-permission.decorator';
import { buildAbilityFor } from './ability.factory';

@Injectable()
export class PermissionsGuard implements CanActivate {
  constructor(private readonly reflector: Reflector) {}

  canActivate(context: ExecutionContext): boolean {
    const required = this.reflector.getAllAndOverride<RequiredPermission | undefined>(
      PERMISSION_KEY,
      [context.getHandler(), context.getClass()],
    );
    if (!required) return true;

    const user: AuthContext | undefined = context.switchToHttp().getRequest().user;
    if (!user) throw new ForbiddenException('غير مصرح');

    const ability = buildAbilityFor(user);
    if (!ability.can(required.action, required.resource)) {
      throw new ForbiddenException(
        `لا تملك صلاحية "${required.action}" على "${required.resource}"`,
      );
    }
    return true;
  }
}
