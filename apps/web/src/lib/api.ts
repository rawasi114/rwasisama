'use client';

import axios from 'axios';
import { useAuthStore } from './auth-store';
import type { LoginResponseDto } from '@rawasi/shared-types';

const baseURL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:4000/api';

export const api = axios.create({ baseURL });

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export async function login(email: string, password: string): Promise<LoginResponseDto> {
  const { data } = await api.post<LoginResponseDto>('/auth/login', { email, password });
  return data;
}

export async function logout(): Promise<void> {
  const { refreshToken } = useAuthStore.getState();
  if (refreshToken) {
    try {
      await api.post('/auth/logout', { refreshToken });
    } catch {
      // ignore network/logout errors; clear locally regardless
    }
  }
  useAuthStore.getState().clear();
}
