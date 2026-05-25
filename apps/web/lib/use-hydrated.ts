import { useEffect, useState } from 'react';

/** يمنع عدم تطابق SSR عند القراءة من مخزن مُستمر (localStorage). */
export function useHasHydrated(): boolean {
  const [hydrated, setHydrated] = useState(false);
  useEffect(() => setHydrated(true), []);
  return hydrated;
}
