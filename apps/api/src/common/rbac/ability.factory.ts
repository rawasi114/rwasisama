import { AbilityBuilder, createMongoAbility, MongoAbility } from '@casl/ability';

export type AppAbility = MongoAbility<[string, string]>;

export interface AbilitySubject {
  permissions: { resource: string; action: string }[];
}

/** يبني صلاحيات CASL من قائمة صلاحيات المستخدم (resource + action). */
export function buildAbilityFor(user: AbilitySubject): AppAbility {
  const { can, build } = new AbilityBuilder<AppAbility>(createMongoAbility);
  for (const p of user.permissions ?? []) {
    can(p.action, p.resource);
  }
  return build();
}
