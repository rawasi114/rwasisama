'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { LogOut, LayoutDashboard } from 'lucide-react';
import { useAuthStore } from '@/lib/auth-store';
import { logout } from '@/lib/api';

export default function DashboardPage() {
  const t = useTranslations('dashboard');
  const tApp = useTranslations('app');
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const accessToken = useAuthStore((s) => s.accessToken);

  useEffect(() => {
    if (!accessToken) {
      router.replace('/login');
    }
  }, [accessToken, router]);

  if (!user) {
    return null;
  }

  const onLogout = async () => {
    await logout();
    router.replace('/login');
  };

  return (
    <div className="min-h-screen">
      <header className="flex items-center justify-between bg-navy px-6 py-4 text-white">
        <div className="flex items-center gap-2">
          <LayoutDashboard className="h-5 w-5 text-gold" />
          <span className="font-bold">{tApp('name')}</span>
        </div>
        <button
          onClick={onLogout}
          className="flex items-center gap-2 rounded-lg bg-navy-900 px-3 py-1.5 text-sm hover:bg-black/30"
        >
          <LogOut className="h-4 w-4" />
          {t('logout')}
        </button>
      </header>

      <main className="p-6">
        <h1 className="mb-4 text-xl font-bold text-navy">{t('title')}</h1>

        <div className="grid gap-4 sm:grid-cols-3">
          <Card label={t('welcome')} value={user.fullNameAr} />
          <Card label={t('role')} value={user.role.nameAr} />
          <Card label={t('permissions')} value={String(user.permissions.length)} />
        </div>

        <div className="mt-6 rounded-xl border border-dashed border-gold-400 bg-white p-8 text-center text-gray-500">
          {t('empty')}
        </div>
      </main>
    </div>
  );
}

function Card({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-white p-5 shadow-sm">
      <p className="text-sm text-gray-500">{label}</p>
      <p className="mt-1 text-lg font-semibold text-navy">{value}</p>
    </div>
  );
}
