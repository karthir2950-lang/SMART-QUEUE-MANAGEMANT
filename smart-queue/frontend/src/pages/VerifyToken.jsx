import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../services/api';

export default function VerifyToken() {
  const { secureToken } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    const verify = async () => {
      try {
        const res = await api.get(`/api/queue/verify/${secureToken}`);
        if (active) {
          setData(res.data);
        }
      } catch (err) {
        if (active) {
          setError(err.response?.data?.detail || 'Invalid or expired token pass.');
        }
      } finally {
        if (active) setLoading(false);
      }
    };

    if (secureToken) {
      verify();
    } else {
      setLoading(false);
      setError('No verification token provided.');
    }

    return () => {
      active = false;
    };
  }, [secureToken]);

  return (
    <div className="min-h-screen bg-[var(--color-canvas)] text-[var(--color-text-main)] flex flex-col justify-between p-4 sm:p-8">
      <header className="max-w-md mx-auto w-full flex items-center justify-between pb-6 border-b border-[var(--color-border-subtle)]">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[var(--color-primary)] text-white font-bold text-lg flex items-center justify-center shadow-xs">
            Q
          </div>
          <div>
            <h1 className="text-lg font-bold">QueueLess AI</h1>
            <p className="text-[10px] text-[var(--color-secondary)] uppercase font-semibold">Pass Verification</p>
          </div>
        </div>
        <Link
          to="/login"
          className="text-xs font-semibold px-3 py-1.5 rounded-xl border border-[var(--color-border-subtle)] hover:bg-[var(--color-surface-hover)]"
        >
          Sign In
        </Link>
      </header>

      <main className="max-w-md mx-auto w-full my-8">
        {loading && (
          <div className="bg-[var(--color-surface)] p-8 rounded-[24px] border border-[var(--color-border-subtle)] text-center">
            <div className="w-8 h-8 border-3 border-[var(--color-primary)] border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
            <p className="text-sm font-medium text-[var(--color-secondary)]">Verifying digital pass...</p>
          </div>
        )}

        {!loading && (error || !data?.valid) && (
          <div className="bg-[var(--color-surface)] p-8 rounded-[24px] border border-red-200 dark:border-red-900/60 text-center">
            <span className="text-4xl block mb-3">⚠️</span>
            <h2 className="text-xl font-bold text-red-600 dark:text-red-400 mb-2">Invalid Pass</h2>
            <p className="text-sm text-[var(--color-secondary)] mb-6">
              {error || data?.message || 'This verification code is either invalid or has expired.'}
            </p>
            <Link
              to="/login"
              className="inline-flex px-5 py-2.5 bg-[var(--color-primary)] text-white font-semibold rounded-xl text-xs uppercase tracking-wider"
            >
              Go to Portal →
            </Link>
          </div>
        )}

        {!loading && data?.valid && (
          <div className="bg-[var(--color-surface)] p-8 rounded-[24px] border border-[var(--color-border-subtle)] shadow-sm">
            <div className="flex items-center justify-between mb-6">
              <span className="text-xs font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
                <span>✓</span> Verified Active Pass
              </span>
              <span className="text-xs font-bold px-3 py-1 rounded-full bg-[var(--color-accent-subtle)] text-[var(--color-primary)] uppercase">
                {data.queue_status}
              </span>
            </div>

            <div className="text-center my-6">
              <p className="text-xs uppercase font-bold text-[var(--color-secondary)] tracking-widest mb-1">
                Token Number
              </p>
              <h2 className="text-6xl font-extrabold text-[var(--color-primary)] tracking-tight">
                {data.token_number}
              </h2>
            </div>

            <div className="border-t border-b border-[var(--color-border-subtle)] py-4 space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-[var(--color-secondary)]">Sector:</span>
                <span className="font-bold">{data.sector || 'N/A'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--color-secondary)]">Organization:</span>
                <span className="font-bold">{data.organization || 'N/A'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--color-secondary)]">Branch:</span>
                <span className="font-bold">{data.branch || 'N/A'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--color-secondary)]">Service:</span>
                <span className="font-bold">{data.service || 'N/A'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--color-secondary)]">Scheduled:</span>
                <span className="font-bold">{data.appointment_date} at {data.appointment_time}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--color-secondary)]">Queue Position:</span>
                <span className="font-bold">#{data.queue_position}</span>
              </div>
              {data.estimated_waiting_time !== null && (
                <div className="flex justify-between">
                  <span className="text-[var(--color-secondary)]">Estimated Wait:</span>
                  <span className="font-bold text-[var(--color-primary)]">{data.estimated_waiting_time} mins</span>
                </div>
              )}
            </div>

            <div className="mt-6 text-center">
              <p className="text-xs text-[var(--color-secondary)]">
                Please present this pass at the reception counter upon arrival.
              </p>
            </div>
          </div>
        )}
      </main>

      <footer className="text-center text-xs text-[var(--color-secondary)] py-4 border-t border-[var(--color-border-subtle)] max-w-md mx-auto w-full">
        QueueLess AI • Universal Smart Queue Verification System
      </footer>
    </div>
  );
}
