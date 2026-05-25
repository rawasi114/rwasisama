'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { useTranslations } from 'next-intl';
import { login } from '@/lib/api';
import { useAuthStore } from '@/lib/auth-store';

interface FormValues {
  email: string;
  password: string;
}

export default function LoginPage() {
  const t = useTranslations('login');
  const tApp = useTranslations('app');
  const router = useRouter();
  const setAuth = useAuthStore((s) => s.setAuth);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>();

  const onSubmit = async (values: FormValues) => {
    setServerError(null);
    try {
      const res = await login(values.email, values.password);
      setAuth({
        user: res.user,
        accessToken: res.accessToken,
        refreshToken: res.refreshToken,
      });
      router.push('/dashboard');
    } catch {
      setServerError(t('error'));
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-md rounded-2xl bg-white p-8 shadow-lg">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-navy">{tApp('name')}</h1>
          <p className="mt-1 text-sm text-gold-600">{tApp('subtitle')}</p>
        </div>

        <h2 className="mb-6 text-lg font-semibold text-navy">{t('title')}</h2>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm text-navy">{t('email')}</label>
            <input
              type="email"
              autoComplete="username"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:border-gold"
              {...register('email', { required: true })}
            />
            {errors.email && <p className="mt-1 text-xs text-red-600">{t('email')}</p>}
          </div>

          <div>
            <label className="mb-1 block text-sm text-navy">{t('password')}</label>
            <input
              type="password"
              autoComplete="current-password"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:border-gold"
              {...register('password', { required: true })}
            />
            {errors.password && (
              <p className="mt-1 text-xs text-red-600">{t('password')}</p>
            )}
          </div>

          {serverError && <p className="text-sm text-red-600">{serverError}</p>}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-lg bg-navy py-2.5 font-semibold text-white transition hover:bg-navy-900 disabled:opacity-60"
          >
            {isSubmitting ? t('loading') : t('submit')}
          </button>
        </form>
      </div>
    </main>
  );
}
