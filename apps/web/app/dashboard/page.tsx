'use client';

import { Building2, FileSpreadsheet, FolderKanban, LogOut } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { useAuthStore } from '@/lib/auth-store';
import { useHasHydrated } from '@/lib/use-hydrated';

const CARDS = [
  { key: 'opportunities', icon: Building2 },
  { key: 'projects', icon: FolderKanban },
  { key: 'boq', icon: FileSpreadsheet },
] as const;

export default function DashboardPage() {
  const t = useTranslations('dashboard');
  const tApp = useTranslations('app');
  const router = useRouter();
  const hydrated = useHasHydrated();
  const user = useAuthStore((s) => s.user);
  const accessToken = useAuthStore((s) => s.accessToken);
  const clear = useAuthStore((s) => s.clear);

  useEffect(() => {
    if (hydrated && !accessToken) router.replace('/login');
  }, [hydrated, accessToken, router]);

  if (!hydrated || !user) {
    return <div className="flex min-h-screen items-center justify-center text-gray-400">...</div>;
  }

  function logout() {
    clear();
    router.replace('/login');
  }

  return (
    <div className="min-h-screen">
      <header className="bg-navy text-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-white/10 text-sm font-bold text-gold">
              رس
            </div>
            <div>
              <p className="text-sm font-semibold leading-tight">{tApp('name')}</p>
              <p className="text-xs text-white/60">{t('title')}</p>
            </div>
          </div>
          <Button onClick={logout} className="bg-white/10 hover:bg-white/20">
            <LogOut className="me-2 h-4 w-4" />
            {t('logout')}
          </Button>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8">
        <div className="mb-6">
          <h1 className="text-xl font-bold text-navy">
            {t('welcome')}، {user.fullNameAr}
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            {t('role')}: <span className="font-medium text-gold">{user.roleNameAr}</span> ·{' '}
            {user.permissions.length} {t('permissions')}
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {CARDS.map(({ key, icon: Icon }) => (
            <Card key={key}>
              <CardHeader>
                <span className="font-semibold text-navy">{t(`cards.${key}`)}</span>
                <Icon className="h-5 w-5 text-gold" />
              </CardHeader>
              <CardContent className="text-sm text-gray-400">{t('cards.soon')}</CardContent>
            </Card>
          ))}
        </div>

        <div className="mt-8 rounded-xl border border-dashed border-gray-300 bg-white/50 p-8 text-center text-sm text-gray-400">
          {t('empty')}
        </div>
      </main>
    </div>
  );
}
