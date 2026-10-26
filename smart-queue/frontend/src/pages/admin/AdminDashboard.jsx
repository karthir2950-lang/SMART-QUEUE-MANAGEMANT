import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../../services/api';

export default function AdminDashboard() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchSummary = async () => {
    try {
      setLoading(true);
      setError('');
      const res = await api.get('/api/admin/dashboard/summary');
      setSummary(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load admin summary');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSummary();
  }, []);

  const kpis = summary
    ? [
        { label: 'Total Organizations', value: summary.total_organizations, icon: '🏢', color: 'from-blue-500/10 to-blue-500/20 text-blue-600 dark:text-blue-400', link: '/admin/organizations' },
        { label: 'Total Branches', value: summary.total_branches, icon: '📍', color: 'from-teal-500/10 to-teal-500/20 text-teal-600 dark:text-teal-400', link: '/admin/branches' },
        { label: 'Total Services', value: summary.total_services, icon: '🛠️', color: 'from-indigo-500/10 to-indigo-500/20 text-indigo-600 dark:text-indigo-400', link: '/admin/services' },
        { label: 'Active Staff', value: summary.total_staff, icon: '👥', color: 'from-purple-500/10 to-purple-500/20 text-purple-600 dark:text-purple-400', link: '/admin/staff' },
        { label: 'Total Counters', value: summary.total_counters, icon: '🎫', color: 'from-amber-500/10 to-amber-500/20 text-amber-600 dark:text-amber-400', link: '/admin/counters' },
        { label: "Today's Appointments", value: summary.today_appointments, icon: '📅', color: 'from-sky-500/10 to-sky-500/20 text-sky-600 dark:text-sky-400', link: '/admin/appointments' },
        { label: 'Active Queue Tokens', value: summary.today_active_tokens, icon: '🎟️', color: 'from-rose-500/10 to-rose-500/20 text-rose-600 dark:text-rose-400', link: '/admin/tokens' },
        { label: 'Completed Today', value: summary.today_completed, icon: '✅', color: 'from-emerald-500/10 to-emerald-500/20 text-emerald-600 dark:text-emerald-400', link: '/admin/appointments' },
      ]
    : [];

  return (
    <div className="max-w-7xl mx-auto pb-12 space-y-8">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-bold uppercase tracking-widest text-[var(--color-primary)]">
            Command Center
          </span>
          <h1 className="text-3xl font-extrabold tracking-tight text-[var(--color-text-main)] mt-1">
            System Administration
          </h1>
          <p className="text-sm text-[var(--color-secondary)] mt-1">
            Real-time platform metrics and verified database relationships.
          </p>
        </div>

        <button
          type="button"
          onClick={fetchSummary}
          disabled={loading}
          className="self-start sm:self-auto px-4 py-2 bg-[var(--color-surface)] border border-[var(--color-border-subtle)] hover:bg-[var(--color-surface-hover)] rounded-xl text-xs font-bold transition-all shadow-xs flex items-center gap-2"
        >
          <span>🔄</span>
          <span>{loading ? 'Refreshing...' : 'Refresh Data'}</span>
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900/60 text-red-700 dark:text-red-400 text-sm font-medium">
          {error}
        </div>
      )}

      {/* Real Database KPI Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {loading && !summary &&
          Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="bg-[var(--color-surface)] p-6 rounded-[22px] border border-[var(--color-border-subtle)] animate-pulse">
              <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2 mb-3"></div>
              <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/3"></div>
            </div>
          ))}

        {!loading &&
          kpis.map((kpi) => (
            <Link
              key={kpi.label}
              to={kpi.link}
              className="bg-[var(--color-surface)] p-6 rounded-[22px] border border-[var(--color-border-subtle)] hover:border-[var(--color-primary)] shadow-xs hover:shadow-md transition-all flex flex-col justify-between group"
            >
              <div className="flex items-center justify-between mb-4">
                <span className="text-xs font-bold text-[var(--color-secondary)] uppercase tracking-wider">
                  {kpi.label}
                </span>
                <span className="text-2xl group-hover:scale-110 transition-transform">{kpi.icon}</span>
              </div>
              <div>
                <p className="text-3xl sm:text-4xl font-extrabold text-[var(--color-text-main)] tracking-tight">
                  {kpi.value}
                </p>
                <p className="text-[11px] text-[var(--color-primary)] font-semibold mt-2 group-hover:underline">
                  Manage record →
                </p>
              </div>
            </Link>
          ))}
      </div>

      {/* Admin Sector Breakdown View (All 6 Sectors) */}
      <div className="bg-[var(--color-surface)] p-6 sm:p-8 rounded-[24px] border border-[var(--color-border-subtle)] shadow-xs">
        <div className="flex items-center justify-between mb-6 pb-4 border-b border-[var(--color-border-subtle)]">
          <div>
            <h2 className="text-xl font-bold text-[var(--color-text-main)]">
              Sector Distribution
            </h2>
            <p className="text-xs text-[var(--color-secondary)] mt-1">
              Active sectors with real organization, branch, and service counts.
            </p>
          </div>
          <span className="text-xs font-bold px-3 py-1 rounded-full bg-[var(--color-accent-subtle)] text-[var(--color-primary)]">
            6 Standard Sectors
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {summary?.sectors?.map((sec) => (
            <div
              key={sec.id}
              className="p-5 rounded-[18px] border border-[var(--color-border-subtle)] bg-[var(--color-canvas)] transition-all"
            >
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-bold text-base text-[var(--color-text-main)]">{sec.name}</h3>
                <span className="text-xs text-[var(--color-secondary)] font-mono">{sec.slug}</span>
              </div>

              <div className="grid grid-cols-3 gap-2 pt-3 border-t border-[var(--color-border-subtle)] text-center">
                <div className="bg-[var(--color-surface)] p-2.5 rounded-xl border border-[var(--color-border-subtle)]">
                  <p className="text-xs text-[var(--color-secondary)]">Orgs</p>
                  <p className="text-lg font-bold text-[var(--color-text-main)] mt-0.5">{sec.total_organizations}</p>
                </div>
                <div className="bg-[var(--color-surface)] p-2.5 rounded-xl border border-[var(--color-border-subtle)]">
                  <p className="text-xs text-[var(--color-secondary)]">Branches</p>
                  <p className="text-lg font-bold text-[var(--color-text-main)] mt-0.5">{sec.total_branches}</p>
                </div>
                <div className="bg-[var(--color-surface)] p-2.5 rounded-xl border border-[var(--color-border-subtle)]">
                  <p className="text-xs text-[var(--color-secondary)]">Services</p>
                  <p className="text-lg font-bold text-[var(--color-text-main)] mt-0.5">{sec.total_services}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
