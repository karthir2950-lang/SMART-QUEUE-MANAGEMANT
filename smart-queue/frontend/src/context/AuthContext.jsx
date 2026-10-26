import React, { createContext, useContext, useEffect, useState } from 'react';
import api, { supabase } from '../services/api';

const AuthContext = createContext({});

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [profile, setProfile] = useState(null);
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchProfile = React.useCallback(async (accessToken) => {
    try {
      let token = accessToken || localStorage.getItem('sq_auth_token');
      if (!token) {
        const { data: { session: s } } = await supabase.auth.getSession();
        token = s?.access_token;
      }
      if (!token) {
        setProfile(null);
        return null;
      }
      const res = await api.get('/api/auth/me', {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.data && res.data.id) {
        setProfile(res.data);
        setUser(res.data);
        return res.data;
      }
      return null;
    } catch (err) {
      console.warn('Profile fetch notice:', err?.message || err);
      try {
        const { data: { session: s } } = await supabase.auth.getSession();
        if (s?.user) {
          const fallback = {
            id: s.user.id,
            email: s.user.email,
            name: s.user.user_metadata?.full_name || s.user.user_metadata?.name || s.user.email?.split('@')[0] || 'User',
            role: s.user.app_metadata?.role || 'USER',
            status: 'ACTIVE',
            can_access_user_portal: true,
            customer_profile_id: s.user.id,
          };
          setProfile(fallback);
          setUser(fallback);
          return fallback;
        }
      } catch {
        // ignore
      }
      setProfile(null);
      return null;
    }
  }, []);

  const setAuthSession = React.useCallback(async (newSession) => {
    setSession(newSession);
    if (newSession?.access_token) {
      try {
        const res = await api.get('/api/auth/me', {
          headers: { Authorization: `Bearer ${newSession.access_token}` }
        });
        if (res.data && res.data.id) {
          setProfile(res.data);
          setUser(res.data);
          setLoading(false);
          return res.data;
        }
      } catch (err) {
        console.warn('setAuthSession profile fetch notice:', err?.message);
        const fallback = {
          id: newSession.user.id,
          email: newSession.user.email,
          name: newSession.user.user_metadata?.full_name || newSession.user.user_metadata?.name || newSession.user.email?.split('@')[0] || 'User',
          role: newSession.user.app_metadata?.role || 'USER',
          status: 'ACTIVE',
          can_access_user_portal: true,
          customer_profile_id: newSession.user.id,
        };
        setProfile(fallback);
        setUser(fallback);
        setLoading(false);
        return fallback;
      }
    }
    setLoading(false);
    return null;
  }, []);

  const loginWithLocalToken = async (token, userData = null) => {
    localStorage.setItem('sq_auth_token', token);
    const profileData = await fetchProfile(token);
    const finalUser = profileData || userData;
    setUser(finalUser);
    setProfile(finalUser);
    return finalUser;
  };

  useEffect(() => {
    let isMounted = true;

    const initAuth = async () => {
      // Prioritize OAuth callback if URL hash or search contains OAuth tokens/codes
      const hasOAuthCallback = 
        typeof window !== 'undefined' && 
        (window.location.hash.includes('access_token=') || 
         window.location.search.includes('code=') ||
         window.location.search.includes('error='));

      if (!hasOAuthCallback) {
        const localToken = localStorage.getItem('sq_auth_token');
        if (localToken) {
          try {
            const prof = await fetchProfile(localToken);
            if (prof && isMounted) {
              setUser(prof);
              setLoading(false);
              return;
            }
          } catch {
            localStorage.removeItem('sq_auth_token');
          }
        }
      }

      // Check Supabase session
      try {
        const { data: { session: currentSession }, error: sessionErr } = await supabase.auth.getSession();
        if (sessionErr) console.warn('Supabase getSession notice:', sessionErr.message);
        if (isMounted) {
          setSession(currentSession);
          if (currentSession?.user) {
            const prof = await fetchProfile(currentSession.access_token);
            if (prof && isMounted) {
              setProfile(prof);
              setUser(prof);
            } else if (isMounted) {
              setUser(currentSession.user);
            }
          } else {
            setUser(null);
            setProfile(null);
          }
        }
      } catch (err) {
        console.warn('Supabase auth session initialization notice:', err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    initAuth();

    let subscription = null;
    try {
      const authListener = supabase.auth.onAuthStateChange(async (event, newSession) => {
        if (!isMounted) return;
        if (event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED' || event === 'USER_UPDATED') {
          setSession(newSession);
          if (newSession?.user) {
            const prof = await fetchProfile(newSession.access_token);
            if (prof && isMounted) {
              setProfile(prof);
              setUser(prof);
            } else if (isMounted) {
              setUser(newSession.user);
            }
          }
          setLoading(false);
        } else if (event === 'SIGNED_OUT') {
          localStorage.removeItem('sq_auth_token');
          setSession(null);
          setUser(null);
          setProfile(null);
          setLoading(false);
        }
      });
      subscription = authListener?.data?.subscription;
    } catch {
      // Supabase listener offline
    }

    return () => {
      isMounted = false;
      if (subscription?.unsubscribe) subscription.unsubscribe();
    };
  }, []);

  const logout = async () => {
    localStorage.removeItem('sq_auth_token');
    try {
      await supabase.auth.signOut();
    } catch {
      // Supabase offline
    }
    setUser(null);
    setProfile(null);
    setSession(null);
  };

  return (
    <AuthContext.Provider value={{ user, profile, session, loading, logout, refreshProfile: fetchProfile, setAuthSession, loginWithLocalToken }}>
      {loading ? (
        <div className="min-h-screen flex items-center justify-center bg-[var(--color-canvas)] text-[var(--color-secondary)]">
          <div className="flex flex-col items-center gap-3">
            <div className="w-8 h-8 border-3 border-[var(--color-primary)] border-t-transparent rounded-full animate-spin"></div>
            <span className="text-sm font-medium">Verifying authentication...</span>
          </div>
        </div>
      ) : (
        children
      )}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
