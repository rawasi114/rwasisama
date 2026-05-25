'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { AuthUserDto } from '@rawasi/shared-types';

interface AuthState {
  user: AuthUserDto | null;
  accessToken: string | null;
  refreshToken: string | null;
  setAuth: (data: {
    user: AuthUserDto;
    accessToken: string;
    refreshToken: string;
  }) => void;
  clear: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      setAuth: ({ user, accessToken, refreshToken }) =>
        set({ user, accessToken, refreshToken }),
      clear: () => set({ user: null, accessToken: null, refreshToken: null }),
    }),
    { name: 'rawasi-auth' },
  ),
);
