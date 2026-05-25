import { Injectable } from '@nestjs/common';
import {
  AbilityBuilder,
  createMongoAbility,
  MongoAbility,
  ExtractSubjectType,
} from '@casl/ability';
import { AuthenticatedUser } from '../types/authenticated-user';

export type AppAbility = MongoAbility<[string, string]>;

@Injectable()
export class CaslAbilityFactory {
  /**
   * Build a CASL ability from the user's flat (action, subject) permissions.
   * "manage" grants any action; "all" grants on any subject.
   */
  createForUser(user: AuthenticatedUser): AppAbility {
    const { can, build } = new AbilityBuilder<AppAbility>(createMongoAbility);

    for (const p of user.permissions ?? []) {
      can(p.action, p.subject);
    }

    return build({
      detectSubjectType: (item) =>
        (typeof item === 'string' ? item : (item as { __caslSubjectType__: string })
          .__caslSubjectType__) as ExtractSubjectType<string>,
    });
  }
}
