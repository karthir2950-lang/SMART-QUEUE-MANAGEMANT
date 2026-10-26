import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { supabase } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';

export default function Login() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialMode = searchParams.get('mode') === 'signup' ? 'signup' : 'login';
  const [mode, setMode] = useState(initialMode); // 'login' or 'signup'
  
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  
  const getInitialError = () => {
    const errorParam = searchParams.get('error_description') || searchParams.get('error');
    if (errorParam) {
      return decodeURIComponent(errorParam.replace(/\+/g, ' '));
    }
    if (typeof window !== 'undefined' && window.location.hash.includes('error=')) {
      const hashParams = new URLSearchParams(window.location.hash.substring(1));
      const hashError = hashParams.get('error_description') || hashParams.get('error');
      if (hashError) {
        return decodeURIComponent(hashError.replace(/\+/g, ' '));
      }
    }
    return '';
  };

  const [error, setError] = useState(getInitialError);
  const [infoMessage, setInfoMessage] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isGoogleSubmitting, setIsGoogleSubmitting] = useState(false);
  const isSigningUpRef = useRef(false);

  const navigate = useNavigate();
  const { user, profile, session, refreshProfile, logout } = useAuth();
  const { themeMode, setThemeMode } = useTheme();

  // If already logged in, redirect based on authentication provider & role
  useEffect(() => {
    // If registration is in progress or just completed, do not auto-redirect
    if (isSigningUpRef.current) return;

    // If an OAuth callback is being processed in URL, delegate to /auth/callback
    const winSearch = typeof window !== 'undefined' ? new URLSearchParams(window.location.search) : null;
    const hashStr = typeof window !== 'undefined' ? window.location.hash : '';
    const hashQuery = hashStr.includes('?') 
      ? new URLSearchParams(hashStr.split('?')[1]) 
      : new URLSearchParams(hashStr.startsWith('#') ? hashStr.slice(1) : hashStr);

    const codeVal = searchParams.get('code') || winSearch?.get('code') || hashQuery.get('code');
    const errVal = searchParams.get('error') || winSearch?.get('error') || hashQuery.get('error');
    const errDesc = searchParams.get('error_description') || winSearch?.get('error_description') || hashQuery.get('error_description');

    const hasOAuth = Boolean(codeVal || errVal || errDesc || hashStr.includes('access_token='));
    if (hasOAuth) {
      const q = new URLSearchParams();
      if (codeVal) q.set('code', codeVal);
      if (errVal) q.set('error', errVal);
      if (errDesc) q.set('error_description', errDesc);
      const queryStr = q.toString() ? `?${q.toString()}` : '';
      navigate(`/auth/callback${queryStr}`, { replace: true });
      return;
    }

    if (user && profile) {
      const provider = session?.user?.app_metadata?.provider || user?.app_metadata?.provider;
      if (provider === 'google') {
        // Google authentication routes directly to user dashboard for citizen features
        navigate('/user/dashboard', { replace: true });
        return;
      }

      // Credential login routes according to role
      const role = profile?.role || 'USER';
      if (role === 'ADMIN') {
        navigate('/admin/dashboard', { replace: true });
      } else if (role === 'STAFF') {
        navigate('/staff/dashboard', { replace: true });
      } else {
        navigate('/user/dashboard', { replace: true });
      }
    }
  }, [user, profile, session, navigate, searchParams]);

  const switchMode = (newMode) => {
    setError('');
    setInfoMessage('');
    setMode(newMode);
    setSearchParams(newMode === 'signup' ? { mode: 'signup' } : {});
  };

  const handleGoogleLogin = async () => {
    if (isGoogleSubmitting || isSubmitting) return;
    setIsGoogleSubmitting(true);
    setError('');
    setInfoMessage('');
    try {
      localStorage.removeItem('sq_auth_token');
      console.log('[Auth] Initiating Google OAuth PKCE flow. Pre-OAuth storage keys:', Object.keys(localStorage));
      const { data, error: oauthError } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: `${window.location.origin}/auth/callback`
        }
      });
      console.log('[Auth] signInWithOAuth complete. Post-OAuth storage keys:', Object.keys(localStorage));
      if (oauthError) {
        setError(oauthError.message || 'Google OAuth could not be initialized');
      } else if (data?.url) {
        window.location.href = data.url;
      }
    } catch (err) {
      setError(err?.message || 'Google OAuth service is currently unreachable. Please check Supabase Google provider configuration.');
    } finally {
      setIsGoogleSubmitting(false);
    }
  };

  const handleEmailAuth = async (e) => {
    e.preventDefault();
    if (isSubmitting || isGoogleSubmitting) return;
    setError('');
    setInfoMessage('');

    const cleanEmail = email.trim();
    if (!cleanEmail) {
      setError('Email is required');
      return;
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(cleanEmail)) {
      setError('Invalid email address format');
      return;
    }

    if (!password) {
      setError('Password is required');
      return;
    }

    if (mode === 'signup') {
      const cleanName = name.trim();
      if (!cleanName) {
        setError('Full Name is required');
        return;
      }
      if (!confirmPassword) {
        setError('Please confirm your password');
        return;
      }
      if (password !== confirmPassword) {
        setError('Passwords do not match');
        return;
      }
      if (password.length < 6) {
        setError('Password must be at least 6 characters');
        return;
      }

      isSigningUpRef.current = true;
      setIsSubmitting(true);
      try {
        localStorage.removeItem('sq_auth_token');
        const { data: signUpData, error: signUpError } = await supabase.auth.signUp({
          email: cleanEmail,
          password: password,
          options: {
            data: { full_name: cleanName }
          }
        });

        if (signUpError) {
          setError(signUpError.message || 'Signup failed. Please try again.');
          setIsSubmitting(false);
          isSigningUpRef.current = false;
          return;
        }

        // Supabase might automatically establish an authenticated session during signUp
        // when email confirmation is disabled. We MUST sign out any newly created session
        // without deleting the newly created account.
        try {
          await supabase.auth.signOut();
        } catch {
          // ignore
        }
        if (logout) {
          try {
            await logout();
          } catch {
            // ignore
          }
        }
        localStorage.removeItem('sq_auth_token');

        // Check if email confirmation is required based on Supabase response
        const isEmailConfirmationRequired = Boolean(
          signUpData?.user &&
          !signUpData.user.confirmed_at &&
          !signUpData.user.email_confirmed_at &&
          !signUpData.session
        );

        if (isEmailConfirmationRequired) {
          setInfoMessage('Account created successfully! Please check your email to verify your account before logging in.');
        } else {
          setInfoMessage('Account created successfully. Please log in.');
        }

        // Do NOT navigate to /user/dashboard. Reset passwords and return to /login
        setPassword('');
        setConfirmPassword('');
        setMode('login');
        setSearchParams({});
        navigate('/login', { replace: true });
      } catch (err) {
        setError(err?.message || 'Signup failed. Please check your connection and try again.');
      } finally {
        setIsSubmitting(false);
        setTimeout(() => {
          isSigningUpRef.current = false;
        }, 1500);
      }
    } else {
      // Login mode with real Supabase Auth credentials verification
      setIsSubmitting(true);
      try {
        localStorage.removeItem('sq_auth_token');
        const { data: signInData, error: signInError } = await supabase.auth.signInWithPassword({
          email: cleanEmail,
          password: password
        });

        if (signInError) {
          setError(signInError.message || 'Incorrect email or password. Please try again.');
          setIsSubmitting(false);
          return;
        }

        if (signInData?.session?.access_token) {
          const profileData = await refreshProfile(signInData.session.access_token);
          const role = profileData?.role || 'USER';
          if (role === 'ADMIN') {
            navigate('/admin/dashboard', { replace: true });
          } else if (role === 'STAFF') {
            navigate('/staff/dashboard', { replace: true });
          } else {
            navigate('/user/dashboard', { replace: true });
          }
          return;
        } else {
          setError('Authentication failed. No active session established.');
        }
      } catch (authErr) {
        setError(authErr?.message || 'Login failed. Please check your credentials and try again.');
      } finally {
        setIsSubmitting(false);
      }
    }
  };

  const handleForgotPassword = async () => {
    if (!email.trim()) {
      setError('Please enter your email address to reset password');
      return;
    }
    setError('');
    setInfoMessage('');
    try {
      const { error: resetErr } = await supabase.auth.resetPasswordForEmail(email.trim(), {
        redirectTo: `${window.location.origin}/login`
      });
      if (resetErr) {
        setError(resetErr.message || 'Could not send reset password email');
      } else {
        setInfoMessage('Password reset link sent to your email.');
      }
    } catch {
      setInfoMessage(`Password reset request recorded for ${email.trim()}. Contact system admin if needed.`);
    }
  };

  const isOAuthCallbackPending = typeof window !== 'undefined' && 
    (window.location.hash.includes('access_token=') || searchParams.has('code'));

  return (
    <div className="min-h-screen flex flex-col justify-between bg-[var(--color-canvas)] text-[var(--color-text-main)] transition-colors duration-200">
      {/* Top bar with logo and theme toggle */}
      <header className="w-full px-6 py-4 flex items-center justify-between border-b border-[var(--color-border-subtle)] bg-[var(--color-surface)]">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[var(--color-primary)] flex items-center justify-center text-white font-bold text-lg shadow-sm">
            Q
          </div>
          <div>
            <span className="font-bold text-lg text-[var(--color-text-main)] tracking-tight">QueueLess AI</span>
            <span className="hidden sm:inline-block ml-2 text-xs text-[var(--color-secondary)] uppercase tracking-wider font-semibold">Universal Queue Platform</span>
          </div>
        </div>

        <button
          type="button"
          onClick={() => setThemeMode(themeMode === 'dark' ? 'light' : 'dark')}
          className="p-2.5 rounded-xl border border-[var(--color-border-subtle)] hover:bg-[var(--color-surface-hover)] text-[var(--color-secondary)] hover:text-[var(--color-text-main)] transition-colors text-sm flex items-center gap-2"
          aria-label="Toggle Dark/Light Mode"
        >
          <span>{themeMode === 'dark' ? '☀️' : '🌙'}</span>
          <span className="hidden sm:inline font-medium text-xs">{themeMode === 'dark' ? 'Light Mode' : 'Dark Mode'}</span>
        </button>
      </header>

      {/* Main Container */}
      <main className="flex-1 flex items-center justify-center p-4 sm:p-6 my-6">
        <div className="bg-[var(--color-surface)] p-8 sm:p-10 rounded-[22px] shadow-sm max-w-md w-full border border-[var(--color-border-subtle)] transition-all">
          
          {/* Header */}
          <div className="text-center mb-8">
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-[var(--color-text-main)] mb-2">
              {mode === 'signup' ? 'Create Account' : 'Welcome Back'}
            </h1>
            <p className="text-sm text-[var(--color-secondary)]">
              {mode === 'signup' 
                ? 'Sign up to manage smart appointments and tokens'
                : 'Sign in to access your queues, tokens and appointments'}
            </p>
          </div>

          {/* OAuth Callback in-progress notification */}
          {isOAuthCallbackPending && !error && (
            <div className="mb-6 p-4 rounded-xl bg-sky-50 dark:bg-sky-950/40 border border-sky-200 dark:border-sky-800 text-sky-800 dark:text-sky-300 text-sm font-medium flex items-center gap-3">
              <div className="w-4 h-4 border-2 border-sky-600 border-t-transparent rounded-full animate-spin"></div>
              <span>Completing Google authentication...</span>
            </div>
          )}

          {/* Alerts */}
          {error && (
            <div className="mb-6 p-4 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900/60 text-red-700 dark:text-red-400 text-sm font-medium flex items-start gap-2.5">
              <span className="text-base leading-none mt-0.5">⚠️</span>
              <div className="flex-1">{error}</div>
            </div>
          )}

          {infoMessage && (
            <div className="mb-6 p-4 rounded-xl bg-teal-50 dark:bg-teal-950/40 border border-teal-200 dark:border-teal-800 text-teal-800 dark:text-teal-300 text-sm font-medium flex items-start gap-2.5">
              <span className="text-base leading-none mt-0.5">ℹ️</span>
              <div className="flex-1">{infoMessage}</div>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleEmailAuth} className="space-y-4">
            {mode === 'signup' && (
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-[var(--color-secondary)] mb-1.5">
                  Full Name
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. John Doe"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  disabled={isSubmitting || isGoogleSubmitting}
                  className="w-full px-4 py-3 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-input-bg)] text-[var(--color-text-main)] placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] text-sm transition-colors"
                />
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-[var(--color-secondary)] mb-1.5">
                Email Address
              </label>
              <input
                type="email"
                required
                placeholder="name@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={isSubmitting || isGoogleSubmitting}
                className="w-full px-4 py-3 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-input-bg)] text-[var(--color-text-main)] placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] text-sm transition-colors"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-xs font-semibold uppercase tracking-wider text-[var(--color-secondary)]">
                  Password
                </label>
                {mode === 'login' && (
                  <button
                    type="button"
                    onClick={handleForgotPassword}
                    className="text-xs font-semibold text-[var(--color-primary)] hover:underline"
                  >
                    Forgot Password?
                  </button>
                )}
              </div>
              <input
                type="password"
                required
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={isSubmitting || isGoogleSubmitting}
                className="w-full px-4 py-3 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-input-bg)] text-[var(--color-text-main)] placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] text-sm transition-colors"
              />
            </div>

            {mode === 'signup' && (
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-[var(--color-secondary)] mb-1.5">
                  Confirm Password
                </label>
                <input
                  type="password"
                  required
                  placeholder="••••••••"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  disabled={isSubmitting || isGoogleSubmitting}
                  className="w-full px-4 py-3 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-input-bg)] text-[var(--color-text-main)] placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] text-sm transition-colors"
                />
              </div>
            )}

            <button
              type="submit"
              disabled={isSubmitting || isGoogleSubmitting}
              className="w-full mt-2 py-3.5 px-4 bg-[var(--color-primary)] hover:opacity-90 active:scale-[0.99] text-white rounded-xl font-semibold text-sm transition-all shadow-sm disabled:opacity-50 disabled:pointer-events-none flex items-center justify-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  <span>{mode === 'signup' ? 'Creating Account...' : 'Logging In...'}</span>
                </>
              ) : (
                <span>{mode === 'signup' ? 'Create Account' : 'Login'}</span>
              )}
            </button>
          </form>

          {/* Divider */}
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-[var(--color-border-subtle)]"></div>
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-[var(--color-surface)] px-3 text-[var(--color-secondary)] font-semibold tracking-wider">
                OR
              </span>
            </div>
          </div>

          {/* Continue with Google Button */}
          <button
            type="button"
            id="google-login-btn"
            onClick={handleGoogleLogin}
            disabled={isGoogleSubmitting || isSubmitting}
            className="w-full py-3 px-4 border border-[var(--color-border-subtle)] hover:bg-[var(--color-surface-hover)] text-[var(--color-text-main)] rounded-xl font-medium text-sm transition-all flex items-center justify-center gap-3 shadow-xs disabled:opacity-50 disabled:pointer-events-none cursor-pointer"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24">
              <path
                fill="#4285F4"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="#34A853"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="#FBBC05"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
              />
              <path
                fill="#EA4335"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
              />
            </svg>
            <span>{isGoogleSubmitting ? 'Connecting...' : 'Continue with Google'}</span>
          </button>

          {/* Footer toggle */}
          <div className="mt-8 text-center text-sm text-[var(--color-secondary)]">
            {mode === 'signup' ? (
              <p>
                Already have an account?{' '}
                <button
                  type="button"
                  onClick={() => switchMode('login')}
                  className="font-semibold text-[var(--color-primary)] hover:underline ml-1"
                >
                  Login
                </button>
              </p>
            ) : (
              <p>
                Don't have an account?{' '}
                <button
                  type="button"
                  onClick={() => switchMode('signup')}
                  className="font-semibold text-[var(--color-primary)] hover:underline ml-1"
                >
                  Sign Up
                </button>
              </p>
            )}
          </div>
        </div>
      </main>

      {/* Footer info */}
      <footer className="py-4 text-center text-xs text-[var(--color-secondary)] border-t border-[var(--color-border-subtle)]">
        QueueLess AI © {new Date().getFullYear()} • Universal Smart Queue & Appointment Management
      </footer>
    </div>
  );
}
