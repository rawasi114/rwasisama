/** Shape of req.user after JWT authentication (loaded fresh from DB). */
export interface AuthenticatedUser {
  id: string;
  email: string;
  fullNameAr: string;
  fullNameEn: string | null;
  role: { id: string; key: string; nameAr: string; nameEn: string };
  permissions: Array<{ action: string; subject: string }>;
}
