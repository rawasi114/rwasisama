// افتراضياً نفس المصدر (same-origin): تطلب الواجهة "/api/..." ويعيد Next توجيهها
// إلى الـ API عبر rewrites (انظر next.config.mjs) — يتجنّب مشاكل CORS في الإنتاج.
export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? '';

export interface Permission {
  resource: string;
  action: string;
}

export interface AuthUser {
  id: string;
  email: string;
  fullNameAr: string;
  fullNameEn: string | null;
  roleName: string;
  roleNameAr: string;
  permissions: Permission[];
}

export interface LoginResponse {
  accessToken: string;
  refreshToken: string;
  user: AuthUser;
}

async function request<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
  const res = await fetch(`${API_BASE}/api${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers ?? {}),
    },
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const message = (data as { message?: string | string[] })?.message ?? 'حدث خطأ غير متوقع';
    throw new Error(Array.isArray(message) ? message.join('، ') : message);
  }
  return data as T;
}

export const api = {
  login: (email: string, password: string) =>
    request<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  me: (token: string) => request<AuthUser>('/auth/me', {}, token),
};
