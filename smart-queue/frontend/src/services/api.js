import axios from 'axios';
import { createClient } from '@supabase/supabase-js';

// Singleton Supabase client instance to guarantee exactly one client in the browser context
function createSupabaseClient() {
  if (typeof window !== 'undefined' && window.__supabaseClient) {
    return window.__supabaseClient;
  }
  const client = createClient(
    import.meta.env.VITE_SUPABASE_URL || 'https://placeholder.supabase.co',
    import.meta.env.VITE_SUPABASE_ANON_KEY || 'placeholder',
    {
      auth: {
        flowType: 'pkce',
        detectSessionInUrl: false, // Disables background auto-exchange so AuthCallback is the single dedicated handler
        persistSession: true,
        autoRefreshToken: true,
        storage: typeof window !== 'undefined' ? window.localStorage : undefined,
      },
    }
  );
  if (typeof window !== 'undefined') {
    window.__supabaseClient = client;
  }
  return client;
}

export const supabase = createSupabaseClient();

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use(
  async (config) => {
    if (!config.headers) {
      config.headers = {};
    }
    const hasAuth = typeof config.headers.get === 'function'
      ? Boolean(config.headers.get('Authorization') || config.headers.get('authorization'))
      : Boolean(config.headers.Authorization || config.headers.authorization);
    if (hasAuth) {
      return config;
    }
    const localToken = localStorage.getItem('sq_auth_token');
    if (localToken) {
      if (typeof config.headers.set === 'function') {
        config.headers.set('Authorization', `Bearer ${localToken}`);
      } else {
        config.headers.Authorization = `Bearer ${localToken}`;
      }
      return config;
    }
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (session?.access_token) {
        if (typeof config.headers.set === 'function') {
          config.headers.set('Authorization', `Bearer ${session.access_token}`);
        } else {
          config.headers.Authorization = `Bearer ${session.access_token}`;
        }
      }
    } catch {
      // Supabase offline fallback
    }
    return config;
  },
  (error) => Promise.reject(error)
);

export default api;
