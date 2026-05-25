// Shared types between the Next.js web app and the NestJS API.

/** Stable machine keys for the 7 personas (mirrors seeded Role.key). */
export const ROLE_KEYS = [
  'CEO',
  'PROJECTS_DIRECTOR',
  'TECH_OFFICE_MANAGER',
  'PLANNING_ENGINEER',
  'SITE_ENGINEER',
  'ACCOUNTANT',
  'EXTERNAL_CONSULTANT',
] as const;

export type RoleKey = (typeof ROLE_KEYS)[number];

/** CASL-style action verbs. */
export type PermissionAction = 'create' | 'read' | 'update' | 'delete' | 'manage';

export interface PermissionDto {
  action: PermissionAction | string;
  subject: string;
}

export interface RoleDto {
  id: string;
  key: string;
  nameAr: string;
  nameEn: string;
}

export interface AuthUserDto {
  id: string;
  email: string;
  fullNameAr: string;
  fullNameEn: string | null;
  role: RoleDto;
  permissions: PermissionDto[];
}

export interface LoginRequestDto {
  email: string;
  password: string;
}

export interface AuthTokensDto {
  accessToken: string;
  refreshToken: string;
}

export interface LoginResponseDto extends AuthTokensDto {
  user: AuthUserDto;
}
