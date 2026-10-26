import React from 'react';
import { useAuth } from '../../context/AuthContext';

export default function Profile() {
  const { user, profile } = useAuth();

  const displayName = profile?.name || user?.user_metadata?.full_name || user?.user_metadata?.name || 'User';
  const displayEmail = user?.email || profile?.email || '';
  const initial = displayName.charAt(0).toUpperCase();

  return (
    <div className="max-w-2xl mx-auto pb-12">
      <div className="mb-6">
        <span className="text-xs font-bold uppercase tracking-widest text-[var(--color-primary)]">
          Account
        </span>
        <h1 className="text-3xl font-bold text-[var(--color-text-main)] mt-1">Profile Overview</h1>
        <p className="text-[var(--color-secondary)] text-sm mt-1">
          Your verified credentials and queue membership.
        </p>
      </div>

      <div className="bg-[var(--color-surface)] p-6 sm:p-8 rounded-[22px] border border-[var(--color-border-subtle)] shadow-xs">
        <div className="flex flex-col sm:flex-row items-center gap-6 mb-8 pb-8 border-b border-[var(--color-border-subtle)] text-center sm:text-left">
          <div className="w-20 h-20 rounded-2xl bg-[var(--color-accent-subtle)] text-[var(--color-primary)] flex items-center justify-center text-3xl font-bold shadow-xs">
            {initial}
          </div>
          <div>
            <h2 className="text-xl font-bold text-[var(--color-text-main)]">{displayName}</h2>
            <p className="text-sm text-[var(--color-secondary)] mt-0.5">{displayEmail}</p>
            <div className="mt-2.5 flex items-center justify-center sm:justify-start gap-2">
              <span className="px-3 py-1 bg-teal-100 text-teal-800 dark:bg-teal-950 dark:text-teal-300 text-xs font-bold uppercase rounded-full tracking-wider">
                {profile?.role || 'USER'}
              </span>
              <span className="px-3 py-1 bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-300 text-xs font-bold uppercase rounded-full tracking-wider">
                Active Member
              </span>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-[var(--color-secondary)] mb-1.5">
              Full Name
            </label>
            <input
              type="text"
              readOnly
              value={displayName}
              className="w-full px-4 py-3 border border-[var(--color-border-subtle)] rounded-xl bg-[var(--color-input-bg)] text-[var(--color-text-main)] text-sm cursor-default"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-[var(--color-secondary)] mb-1.5">
              Email Address
            </label>
            <input
              type="email"
              readOnly
              value={displayEmail}
              className="w-full px-4 py-3 border border-[var(--color-border-subtle)] rounded-xl bg-[var(--color-input-bg)] text-[var(--color-text-main)] text-sm cursor-default"
            />
          </div>

          <div className="pt-2 text-xs text-[var(--color-secondary)]">
            🔒 Authentication profile is securely synced with your active session.
          </div>
        </div>
      </div>
    </div>
  );
}
