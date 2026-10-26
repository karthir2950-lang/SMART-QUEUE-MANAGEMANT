import React, { useState, useEffect } from 'react';
import api from '../../services/api';

export default function StaffTokens() {
  const [tokens, setTokens] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Filters
  const [selectedStatus, setSelectedStatus] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  const loadTokens = async () => {
    try {
      setLoading(true);
      setError('');
      const res = await api.get('/api/staff/tokens', {
        params: {
          status: selectedStatus || undefined,
          search: searchTerm || undefined
        }
      });
      setTokens(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load tokens');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTokens();
  }, [selectedStatus]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    loadTokens();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--color-text-main)]">
            Branch Queue Stream
          </h1>
          <p className="text-xs text-[var(--color-secondary)] mt-1">
            Active tokens and waiting tickets assigned to this branch location (Read-Only)
          </p>
        </div>
        <button
          onClick={loadTokens}
          className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface)] text-xs font-semibold text-[var(--color-text-main)] hover:bg-[var(--color-surface-hover)] shadow-xs"
        >
          <span>🔄</span>
          <span>Refresh</span>
        </button>
      </div>

      {/* Step 9 Live Queue Engine Banner */}
      <div className="p-4 rounded-xl border border-emerald-200 dark:border-emerald-900 bg-emerald-50/80 dark:bg-emerald-950/30 flex items-start gap-3">
        <span className="text-lg">⚡</span>
        <div>
          <p className="text-xs font-bold text-emerald-900 dark:text-emerald-200">
            Real-Time Queue Engine & Live Notifications Active
          </p>
          <p className="text-[11px] text-emerald-700 dark:text-emerald-300 mt-0.5">
            Operational queue controls (<strong>Call Next</strong>, <strong>Start Serving</strong>, <strong>Complete</strong>, <strong>Skip</strong>, and <strong>No-Show</strong>) and automated citizen notifications are managed live on your <strong>Staff Dashboard</strong>.
          </p>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="p-4 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface)] flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
        <form onSubmit={handleSearchSubmit} className="flex-1 flex gap-2">
          <input
            type="text"
            placeholder="Search by token number (e.g. HOS-001)..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="flex-1 px-3.5 py-2 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-canvas)] text-xs text-[var(--color-text-main)] focus:outline-hidden focus:ring-2 focus:ring-[var(--color-primary)]"
          />
          <button
            type="submit"
            className="px-4 py-2 rounded-xl bg-[var(--color-canvas)] border border-[var(--color-border-subtle)] text-xs font-semibold text-[var(--color-text-main)] hover:bg-[var(--color-surface-hover)]"
          >
            Search
          </button>
        </form>

        <div className="flex flex-wrap gap-2 items-center">
          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="px-3 py-2 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-canvas)] text-xs text-[var(--color-text-main)] focus:outline-hidden"
          >
            <option value="">All Statuses</option>
            <option value="WAITING">Waiting</option>
            <option value="CALLED">Called</option>
            <option value="SERVING">Serving</option>
            <option value="COMPLETED">Completed</option>
            <option value="CANCELLED">Cancelled</option>
          </select>

          {(selectedStatus || searchTerm) && (
            <button
              onClick={() => {
                setSelectedStatus('');
                setSearchTerm('');
                setTimeout(loadTokens, 0);
              }}
              className="text-xs text-[var(--color-primary)] hover:underline font-semibold px-2 py-1"
            >
              Reset
            </button>
          )}
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="p-4 rounded-xl border border-red-200 bg-red-50 text-red-700 text-xs">
          {error}
        </div>
      )}

      {/* Tokens Table */}
      <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface)] overflow-hidden shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-[var(--color-border-subtle)] bg-[var(--color-canvas)] text-[11px] font-semibold text-[var(--color-secondary)] uppercase tracking-wider">
                <th className="py-3 px-4">Token #</th>
                <th className="py-3 px-4">Service</th>
                <th className="py-3 px-4">Queue Pos</th>
                <th className="py-3 px-4">Est Wait</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Issued At</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-border-subtle)] text-xs">
              {loading ? (
                <tr>
                  <td colSpan="6" className="py-8 text-center text-[var(--color-secondary)]">
                    Loading tokens stream...
                  </td>
                </tr>
              ) : tokens.length === 0 ? (
                <tr>
                  <td colSpan="6" className="py-8 text-center text-[var(--color-secondary)]">
                    No queue tokens found matching current filters.
                  </td>
                </tr>
              ) : (
                tokens.map((t) => {
                  const isWaiting = t.status === 'WAITING';
                  const isCalled = t.status === 'CALLED';
                  const isServing = t.status === 'SERVING';
                  const isCompleted = t.status === 'COMPLETED';

                  return (
                    <tr key={t.id} className="hover:bg-[var(--color-canvas)]/50 transition-colors">
                      <td className="py-3.5 px-4 font-mono">
                        <span className="px-2.5 py-1 rounded-md bg-[var(--color-accent-subtle)] text-[var(--color-primary)] font-bold">
                          {t.token_number}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 font-medium text-[var(--color-text-main)]">
                        {t.service_name || 'Desk Service'}
                      </td>
                      <td className="py-3.5 px-4 font-bold text-[var(--color-text-main)]">
                        {t.queue_position !== null ? `#${t.queue_position}` : '—'}
                      </td>
                      <td className="py-3.5 px-4 text-[var(--color-secondary)]">
                        {t.estimated_waiting_time !== null ? `${t.estimated_waiting_time} mins` : '—'}
                      </td>
                      <td className="py-3.5 px-4">
                        <span
                          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold ${
                            isServing
                              ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300'
                              : isCalled
                              ? 'bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-300'
                              : isWaiting
                              ? 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300'
                              : isCompleted
                              ? 'bg-teal-100 text-teal-800 dark:bg-teal-950 dark:text-teal-300'
                              : 'bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300'
                          }`}
                        >
                          {t.status}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-[var(--color-secondary)]">
                        {t.created_at ? new Date(t.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—'}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
