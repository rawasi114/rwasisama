import { createParamDecorator, ExecutionContext } from '@nestjs/common';

export interface AuthContext {
  id: string;
  email: string;
  fullNameAr: string;
  fullNameEn: string | null;
  isActive: boolean;
  roleName: string;
  roleNameAr: string;
  permissions: { resource: string; action: string }[];
}

/** يُرجِع المستخدم الحالي (أو حقلاً منه) من الطلب. */
export const CurrentUser = createParamDecorator(
  (data: keyof AuthContext | undefined, ctx: ExecutionContext) => {
    const request = ctx.switchToHttp().getRequest();
    const user: AuthContext | undefined = request.user;
    return data ? user?.[data] : user;
  },
);
