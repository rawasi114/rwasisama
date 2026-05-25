import { ForbiddenException } from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { CaslAbilityFactory } from '../casl/casl-ability.factory';
import { PoliciesGuard } from './policies.guard';
import { AuthenticatedUser } from '../types/authenticated-user';

function ctxWith(user: AuthenticatedUser | undefined): any {
  return {
    switchToHttp: () => ({ getRequest: () => ({ user }) }),
    getHandler: () => ({}),
    getClass: () => ({}),
  };
}

const reader: AuthenticatedUser = {
  id: 'u1',
  email: 'x@y.z',
  fullNameAr: 'قارئ',
  fullNameEn: null,
  role: { id: 'r1', key: 'ACCOUNTANT', nameAr: 'محاسب', nameEn: 'Accountant' },
  permissions: [{ action: 'read', subject: 'File' }],
};

describe('PoliciesGuard', () => {
  const factory = new CaslAbilityFactory();

  function guardWith(handlers: any[]): PoliciesGuard {
    const reflector = {
      getAllAndOverride: jest.fn().mockReturnValue(handlers),
    } as unknown as Reflector;
    return new PoliciesGuard(reflector, factory);
  }

  it('allows when there are no policy handlers', () => {
    const guard = guardWith([]);
    expect(guard.canActivate(ctxWith(reader))).toBe(true);
  });

  it('allows when the policy is satisfied', () => {
    const guard = guardWith([(a: any) => a.can('read', 'File')]);
    expect(guard.canActivate(ctxWith(reader))).toBe(true);
  });

  it('forbids when the policy is not satisfied', () => {
    const guard = guardWith([(a: any) => a.can('delete', 'File')]);
    expect(() => guard.canActivate(ctxWith(reader))).toThrow(ForbiddenException);
  });

  it('forbids when there is no authenticated user', () => {
    const guard = guardWith([(a: any) => a.can('read', 'File')]);
    expect(() => guard.canActivate(ctxWith(undefined))).toThrow(ForbiddenException);
  });
});
