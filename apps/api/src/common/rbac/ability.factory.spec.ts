import { buildAbilityFor } from './ability.factory';

describe('buildAbilityFor', () => {
  it('grants only the listed permissions', () => {
    const ability = buildAbilityFor({
      permissions: [
        { resource: 'project', action: 'read' },
        { resource: 'material_request', action: 'create' },
      ],
    });

    expect(ability.can('read', 'project')).toBe(true);
    expect(ability.can('create', 'material_request')).toBe(true);
    expect(ability.can('update', 'project')).toBe(false);
    expect(ability.can('read', 'pricing_intelligence')).toBe(false);
  });

  it('denies everything for an empty permission set', () => {
    const ability = buildAbilityFor({ permissions: [] });
    expect(ability.can('read', 'project')).toBe(false);
  });
});
