import {
  CanActivate,
  ExecutionContext,
  ForbiddenException,
  Injectable,
} from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { CaslAbilityFactory } from '../casl/casl-ability.factory';
import {
  CHECK_POLICIES_KEY,
  PolicyHandler,
} from '../decorators/check-policies.decorator';
import { AuthenticatedUser } from '../types/authenticated-user';

/** Enforces @CheckPolicies(...) handlers against the caller's CASL ability. */
@Injectable()
export class PoliciesGuard implements CanActivate {
  constructor(
    private readonly reflector: Reflector,
    private readonly caslAbilityFactory: CaslAbilityFactory,
  ) {}

  canActivate(context: ExecutionContext): boolean {
    const handlers =
      this.reflector.getAllAndOverride<PolicyHandler[]>(CHECK_POLICIES_KEY, [
        context.getHandler(),
        context.getClass(),
      ]) ?? [];

    if (handlers.length === 0) {
      return true;
    }

    const user = context.switchToHttp().getRequest().user as AuthenticatedUser;
    if (!user) {
      throw new ForbiddenException('غير مصرّح: المستخدم غير معروف');
    }

    const ability = this.caslAbilityFactory.createForUser(user);
    const allowed = handlers.every((h) => h(ability));
    if (!allowed) {
      throw new ForbiddenException('ليس لديك صلاحية للقيام بهذا الإجراء');
    }
    return true;
  }
}
