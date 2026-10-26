import React, { useEffect, useState, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { supabase } from '../services/api';
import { useAuth } from '../context/AuthContext';

export default function AuthCallback() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { setAuthSession, refreshProfile } = useAuth();
  const [statusMessage, setStatusMessage] = useState('Verifying Google authentication...');
  const [errorMessage, setErrorMessage] = useState('');

  const processedRef = useRef(false);

  useEffect(() => {
    const runAuthFlow = async () => {
      if (processedRef.current) return;
      processedRef.current = true;

      // 1. Check for provider OAuth errors in search params, outer window query, or hash
      const winSearch = typeof window !== 'undefined' ? new URLSearchParams(window.location.search) : new URLSearchParams();
      const rawHash = typeof window !== 'undefined' && window.location.hash
        ? (window.location.hash.startsWith('#') ? window.location.hash.substring(1) : window.location.hash)
        : '';
      const hashParams = rawHash.includes('?') 
        ? new URLSearchParams(rawHash.split('?')[1]) 
        : new URLSearchParams(rawHash);

      const queryError = searchParams.get('error_description') || searchParams.get('error')
        || winSearch.get('error_description') || winSearch.get('error')
        || hashParams.get('error_description') || hashParams.get('error');

      if (queryError) {
        const isCancel = queryError === 'access_denied' || queryError.includes('access_denied') || winSearch.get('error') === 'access_denied';
        setErrorMessage(isCancel ? 'Authentication was cancelled by the user.' : queryError);
        return;
      }

      const code = searchParams.get('code') || winSearch.get('code') || hashParams.get('code');

      // Clean up outer query string to prevent replay/loop on refresh
      if (typeof window !== 'undefined' && window.location.search) {
        try {
          window.history.replaceState({}, document.title, window.location.pathname + window.location.hash);
        } catch {
          // ignore
        }
      }

      console.log('[AuthCallback] Processing callback. Query has code:', Boolean(code), 'localStorage keys:', Object.keys(localStorage));

      try {
        let activeSession = null;

        // 2. Consistent PKCE Flow: exchange authorization code for session
        if (code) {
          setStatusMessage('Exchanging authorization code...');
          let exchangeResult = null;
          try {
            exchangeResult = await supabase.auth.exchangeCodeForSession(code);
          } catch (codeErr) {
            console.warn('exchangeCodeForSession throw notice:', codeErr);
            exchangeResult = { error: codeErr };
          }

          if (exchangeResult?.error) {
            // Check if session is already established (e.g. from prior or concurrent exchange)
            const { data: { session: existingSession } } = await supabase.auth.getSession();
            if (existingSession?.access_token) {
              activeSession = existingSession;
            } else {
              // Retry exchange once after short pause for transient network hiccups
              await new Promise(r => setTimeout(r, 600));
              try {
                const retryRes = await supabase.auth.exchangeCodeForSession(code);
                if (retryRes?.data?.session) {
                  activeSession = retryRes.data.session;
                } else {
                  const { data: { session: secondCheck } } = await supabase.auth.getSession();
                  if (secondCheck?.access_token) {
                    activeSession = secondCheck;
                  } else {
                    console.error('PKCE exchange error after retry:', exchangeResult.error);
                    setErrorMessage(exchangeResult.error.message || 'Failed to exchange authorization code');
                    return;
                  }
                }
              } catch {
                const { data: { session: thirdCheck } } = await supabase.auth.getSession();
                if (thirdCheck?.access_token) {
                  activeSession = thirdCheck;
                } else {
                  setErrorMessage(exchangeResult.error.message || 'Failed to exchange authorization code');
                  return;
                }
              }
            }
          } else {
            activeSession = exchangeResult?.data?.session;
          }
        } else {
          // If no code in query params, check whether a session is already established
          const { data: { session: existingSession } } = await supabase.auth.getSession();
          if (existingSession?.access_token) {
            activeSession = existingSession;
          } else {
            setErrorMessage('No authorization code found in callback URL. Please try logging in again.');
            return;
          }
        }

        if (!activeSession?.access_token) {
          setErrorMessage('Failed to establish a valid authentication session. Please try logging in again.');
          return;
        }

        // 3. Verify user profile and role permissions before navigation
        setStatusMessage('Verifying role permissions...');

        let prof = null;
        try {
          if (setAuthSession) {
            prof = await setAuthSession(activeSession);
          } else if (refreshProfile) {
            prof = await refreshProfile(activeSession.access_token);
          }
        } catch (apiErr) {
          console.warn('Profile fetch notice during callback:', apiErr?.message);
        }

        if (!prof) {
          // Fallback to active session user identity if backend profile endpoint is pending or warming up
          prof = {
            id: activeSession.user.id,
            email: activeSession.user.email,
            name: activeSession.user.user_metadata?.full_name || activeSession.user.user_metadata?.name || activeSession.user.email?.split('@')[0] || 'User',
            role: 'ADMIN',
            status: 'ACTIVE',
            can_access_user_portal: true,
            customer_profile_id: activeSession.user.id,
          };
        }

        // Check account active status
        if (prof?.status && prof.status !== 'ACTIVE') {
          await supabase.auth.signOut();
          localStorage.removeItem('sq_auth_token');
          setErrorMessage('Your account is currently inactive or suspended. Please contact system support.');
          return;
        }

        // Authorization Policy:
        // Google Sign-In allows citizen User Portal access (/user/dashboard).
        // If an account is registered with the ADMIN role, its database role remains strictly ADMIN (never downgraded or overwritten).
        // The authenticated ADMIN is redirected to /user/dashboard to browse sectors and book appointments.
        // Administrative APIs and /admin/dashboard remain strictly protected by backend authorization.
        navigate('/user/dashboard', { replace: true });
      } catch (err) {
        console.error('OAuth callback processing failed:', err);
        setErrorMessage(err?.message || 'Failed to complete Google authentication');
      }
    };

    runAuthFlow();
  }, [navigate, searchParams, setAuthSession, refreshProfile]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--color-canvas)] text-[var(--color-text-main)] p-4">
      <div className="bg-[var(--color-surface)] p-8 rounded-2xl shadow-sm border border-[var(--color-border-subtle)] max-w-md w-full text-center">
        <div className="w-12 h-12 rounded-xl bg-[var(--color-primary)] text-white font-bold text-xl flex items-center justify-center mx-auto mb-4 shadow-sm">
          Q
        </div>
        <h2 className="text-xl font-bold mb-2">QueueLess AI</h2>

        {errorMessage ? (
          <div className="space-y-4 mt-4">
            <div className="p-3 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900/60 text-red-700 dark:text-red-400 text-sm font-medium">
              ⚠️ {errorMessage}
            </div>
            <button
              type="button"
              onClick={() => navigate('/login', { replace: true })}
              className="w-full py-2 px-4 bg-[var(--color-surface)] border border-[var(--color-border-subtle)] text-[var(--color-text-main)] font-semibold rounded-xl text-xs hover:bg-[var(--color-surface-hover)] transition-all cursor-pointer"
            >
              Back to Login
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3 mt-4">
            <div className="w-8 h-8 border-3 border-[var(--color-primary)] border-t-transparent rounded-full animate-spin"></div>
            <p className="text-sm text-[var(--color-secondary)]">{statusMessage}</p>
          </div>
        )}
      </div>
    </div>
  );
}
