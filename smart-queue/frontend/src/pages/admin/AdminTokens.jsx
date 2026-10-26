import React, { useState, useEffect } from 'react';
import api from '../../services/api';

export default function AdminTokens() {
  const [tokens, setTokens] = useState([]);
  const [branches, setBranches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Filters
  const [selectedBranch, setSelectedBranch] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');
  const [selectedDate, setSelectedDate] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  const loadData = async () => {
    try {
      setLoading(true);
      setError('');
      const [tokensRes, branchesRes] = await Promise.all([
        api.get('/api/admin/tokens', {
          params: {
            branch_id: selectedBranch || undefined,
            status: selectedStatus || undefined,
            date: selectedDate || undefined,
            search: searchTerm || undefined
          }
        }),
        api.get('/api/admin/branches')
      ]);
      setTokens(tokensRes.data);
      setBranches(branchesRes.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load tokens');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedBranch, selectedStatus, selectedDate]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    loadData();
  };

  // Metrics
  const totalCount = tokens.length;
  const waitingCount = tokens.filter((t) => t.status === 'WAITING').length;
  const calledCount = tokens.filter((t) => t.status === 'CALLED').length;
  const servingCount = tokens.filter((t) => t.status === 'SERVING').length;
  const completedCount = tokens.filter((t) => t.status === 'COMPLETED').length;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--color-text-main)]">
            Queue Tokens Monitor
          </h1>
          <p className="text-xs text-[var(--color-secondary)] mt-1">
            Real-time queue ticket records across branches and service categories (Read-Only)
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={loadData}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface)] text-xs font-semibold text-[var(--color-text-main)] hover:bg-[var(--color-surface-hover)] shadow-xs"
          >
            <span>🔄</span>
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Step 8 Notice Banner */}
      <div className="p-4 rounded-xl border border-blue-200 dark:border-blue-900 bg-blue-50/80 dark:bg-blue-950/30 flex items-start gap-3">
        <span className="text-lg">ℹ️</span>
        <div>
          <p className="text-xs font-bold text-blue-900 dark:text-blue-200">
            Phase Guard Notice (STEP 7)
          </p>
          <p className="text-[11px] text-blue-700 dark:text-blue-300 mt-0.5">
            Operational queue controls (Call Next, Start Serving, Complete, Skip, and Realtime WebSocket updates) are disabled and will be enabled in STEP 8.
          </p>
        </div>
      </div>

      {/* Metrics Ribbon */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        <div className="p-3.5 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface)]">
          <p className="text-[10px] font-semibold text-[var(--color-secondary)] uppercase tracking-wider">Total Tokens</p>
          <p className="text-xl font-black text-[var(--color-text-main)] mt-0.5">{totalCount}</p>
        </div>
        <div className="p-3.5 rounded-xl border border-amber-100 dark:border-amber-950 bg-amber-50/40 dark:bg-amber-950/20">
          <p className="text-[10px] font-semibold text-amber-700 dark:text-amber-400 uppercase tracking-wider">Waiting</p>
          <p className="text-xl font-black text-amber-800 dark:text-amber-300 mt-0.5">{waitingCount}</p>
        </div>
        <div className="p-3.5 rounded-xl border border-purple-100 dark:border-purple-950 bg-purple-50/40 dark:bg-purple-950/20">
          <p className="text-[10px] font-semibold text-purple-700 dark:text-purple-400 uppercase tracking-wider">Called</p>
          <p className="text-xl font-black text-purple-800 dark:text-purple-300 mt-0.5">{calledCount}</p>
        </div>
        <div className="p-3.5 rounded-xl border border-emerald-100 dark:border-emerald-950 bg-emerald-50/40 dark:bg-emerald-950/20">
          <p className="text-[10px] font-semibold text-emerald-700 dark:text-emerald-400 uppercase tracking-wider">Serving</p>
          <p className="text-xl font-black text-emerald-800 dark:text-emerald-300 mt-0.5">{servingCount}</p>
        </div>
        <div className="p-3.5 rounded-xl border border-teal-100 dark:border-teal-950 bg-teal-50/40 dark:bg-teal-950/20">
          <p className="text-[10px] font-semibold text-teal-700 dark:text-teal-400 uppercase tracking-wider">Completed</p>
          <p className="text-xl font-black text-teal-800 dark:text-teal-300 mt-0.5">{completedCount}</p>
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
          {/* Date Picker */}
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="px-3 py-2 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-canvas)] text-xs text-[var(--color-text-main)] focus:outline-hidden"
          />

          {/* Branch Filter */}
          <select
            value={selectedBranch}
            onChange={(e) => setSelectedBranch(e.target.value)}
            className="px-3 py-2 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-canvas)] text-xs text-[var(--color-text-main)] focus:outline-hidden"
          >
            <option value="">All Branches</option>
            {branches.map((b) => (
              <option key={b.id} value={b.id}>{b.city} • {b.name || b.address}</option>
            ))}
          </select>

          {/* Status Filter */}
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
            <option value="NO_SHOW">No Show</option>
          </select>

          {(selectedBranch || selectedStatus || selectedDate || searchTerm) && (
            <button
              onClick={() => {
                setSelectedBranch('');
                setSelectedStatus('');
                setSelectedDate('');
                setSearchTerm('');
                setTimeout(loadData, 0);
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
                <th className="py-3 px-4">Branch</th>
                <th className="py-3 px-4">Queue Pos</th>
                <th className="py-3 px-4">Est Wait</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Issued At</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-border-subtle)] text-xs">
              {loading ? (
                <tr>
                  <td colSpan="7" className="py-8 text-center text-[var(--color-secondary)]">
                    Loading tokens stream...
                  </td>
                </tr>
              ) : tokens.length === 0 ? (
                <tr>
                  <td colSpan="7" className="py-8 text-center text-[var(--color-secondary)]">
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
                        {t.service_name || 'Service Window'}
                      </td>
                      <td className="py-3.5 px-4 text-[var(--color-secondary)]">
                        {t.branch_name || 'Branch'}
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
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${
                              isServing
                                ? 'bg-emerald-500'
                                : isCalled
                                ? 'bg-purple-500'
                                : isWaiting
                                ? 'bg-amber-500'
                                : isCompleted
                                ? 'bg-teal-500'
                                : 'bg-slate-400'
                            }`}
                          />
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
