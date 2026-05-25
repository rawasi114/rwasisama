import { CaslAbilityFactory } from './casl-ability.factory';
import { AuthenticatedUser } from '../types/authenticated-user';

function userWith(permissions: Array<{ action: string; subject: string }>): AuthenticatedUser {
  return {
    id: 'u1',
    email: 'x@y.z',
    fullNameAr: 'مستخدم',
    fullNameEn: null,
    role: { id: 'r1', key: 'TEST', nameAr: 'اختبار', nameEn: 'Test' },
    permissions,
  };
}

describe('CaslAbilityFactory', () => {
  const factory = new CaslAbilityFactory();

  it('grants a specific (action, subject) permission only', () => {
    const ability = factory.createForUser(userWith([{ action: 'read', subject: 'User' }]));
    expect(ability.can('read', 'User')).toBe(true);
    expect(ability.can('update', 'User')).toBe(false);
    expect(ability.can('read', 'File')).toBe(false);
  });

  it('"manage" allows any action on the subject', () => {
    const ability = factory.createForUser(userWith([{ action: 'manage', subject: 'File' }]));
    expect(ability.can('create', 'File')).toBe(true);
    expect(ability.can('delete', 'File')).toBe(true);
  });

  it('"manage all" (CEO) allows everything', () => {
    const ability = factory.createForUser(userWith([{ action: 'manage', subject: 'all' }]));
    expect(ability.can('read', 'User')).toBe(true);
    expect(ability.can('delete', 'AnythingElse')).toBe(true);
  });

  it('denies when user has no permissions', () => {
    const ability = factory.createForUser(userWith([]));
    expect(ability.can('read', 'Dashboard')).toBe(false);
  });
});
