import { SetMetadata } from '@nestjs/common';
import { AppAbility } from '../casl/casl-ability.factory';

export interface PolicyHandler {
  (ability: AppAbility): boolean;
}

export const CHECK_POLICIES_KEY = 'check_policies';

/**
 * Attaches one or more policy checks to a route. Each handler receives the
 * caller's CASL ability and must return true to allow access.
 *
 * Example: @CheckPolicies((a) => a.can('read', 'User'))
 */
export const CheckPolicies = (...handlers: PolicyHandler[]) =>
  SetMetadata(CHECK_POLICIES_KEY, handlers);
