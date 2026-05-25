'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { api } from '@/lib/api';
import { useAuthStore } from '@/lib/auth-store';

const schema = z.object({
  email: z.string().email('بريد إلكتروني غير صالح'),
  password: z.string().min(1, 'كلمة المرور مطلوبة'),
});

type FormData = z.infer<typeof schema>;

export default function LoginPage() {
  const t = useTranslations('login');
  const tApp = useTranslations('app');
  const router = useRouter();
  const setAuth = useAuthStore((s) => s.setAuth);
  const accessToken = useAuthStore((s) => s.accessToken);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema), defaultValues: { email: '', password: '' } });

  useEffect(() => {
    if (accessToken) router.replace('/dashboard');
  }, [accessToken, router]);

  async function onSubmit(data: FormData) {
    setServerError(null);
    try {
      const res = await api.login(data.email, data.password);
      setAuth(res);
      router.replace('/dashboard');
    } catch (e) {
      setServerError(e instanceof Error ? e.message : t('error'));
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-3 flex h-16 w-16 items-center justify-center rounded-2xl bg-navy text-2xl font-bold text-gold">
            رس
          </div>
          <h1 className="text-2xl font-bold text-navy">{tApp('name')}</h1>
          <p className="mt-1 text-sm text-gray-500">{tApp('subtitle')}</p>
        </div>

        <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="mb-5 text-lg font-semibold text-navy">{t('title')}</h2>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
            <div>
              <Label htmlFor="email">{t('email')}</Label>
              <Input id="email" type="email" autoComplete="email" dir="ltr" {...register('email')} />
              {errors.email && <p className="mt-1 text-xs text-red-600">{errors.email.message}</p>}
            </div>
            <div>
              <Label htmlFor="password">{t('password')}</Label>
              <Input id="password" type="password" autoComplete="current-password" {...register('password')} />
              {errors.password && <p className="mt-1 text-xs text-red-600">{errors.password.message}</p>}
            </div>
            {serverError && (
              <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{serverError}</div>
            )}
            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? t('submitting') : t('submit')}
            </Button>
          </form>
        </div>

        <p className="mt-6 text-center text-xs text-gray-400">© رواسي سما للمقاولات</p>
      </div>
    </main>
  );
}
