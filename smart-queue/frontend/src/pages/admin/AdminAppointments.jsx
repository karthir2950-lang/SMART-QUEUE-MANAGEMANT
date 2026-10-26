import React, { useState, useEffect } from 'react';
import api from '../../services/api';

export default function AdminAppointments() {
  const [appointments, setAppointments] = useState([]);
  const [organizations, setOrganizations] = useState([]);
  const [branches, setBranches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Filters
  const [selectedOrg, setSelectedOrg] = useState('');
  const [selectedBranch, setSelectedBranch] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');
  const [selectedDate, setSelectedDate] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  const loadData = async () => {
    try {
      setLoading(true);
      setError('');
      const [apptsRes, orgsRes] = await Promise.all([
        api.get('/api/admin/appointments', {
          params: {
            organization_id: selectedOrg || undefined,
            branch_id: selectedBranch || undefined,
            status: selectedStatus || undefined,
            date: selectedDate || undefined,
            search: searchTerm || undefined
          }
        }),
        api.get('/api/admin/organizations')
      ]);
      setAppointments(apptsRes.data);
      setOrganizations(orgsRes.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load appointments');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedBranch, selectedStatus, selectedDate]);

  useEffect(() => {
    const fetchBranches = async () => {
      if (!selectedOrg) {
        setBranches([]);
        setSelectedBranch('');
        return;
      }
      try {
        const res = await api.get('/api/admin/branches', {
          params: { organization_id: selectedOrg }
        });
        setBranches(res.data);
      } catch (err) {
        console.error('Failed to load branches', err);
      }
    };
    fetchBranches();
  }, [selectedOrg]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    loadData();
  };

  // Metrics
  const totalCount = appointments.length;
  const scheduledCount = appointments.filter((a) => a.status === 'SCHEDULED').length;
  const confirmedCount = appointments.filter((a) => a.status === 'CONFIRMED').length;
  const completedCount = appointments.filter((a) => a.status === 'COMPLETED').length;
  const cancelledCount = appointments.filter((a) => a.status === 'CANCELLED').length;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--color-text-main)]">
            Appointments Directory
          </h1>
          <p className="text-xs text-[var(--color-secondary)] mt-1">
            Master scheduled bookings across sectors, organizations, and branches (Read-Only)
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

      {/* Metrics Ribbon */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        <div className="p-3.5 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface)]">
          <p className="text-[10px] font-semibold text-[var(--color-secondary)] uppercase tracking-wider">Total Records</p>
          <p className="text-xl font-black text-[var(--color-text-main)] mt-0.5">{totalCount}</p>
        </div>
        <div className="p-3.5 rounded-xl border border-blue-100 dark:border-blue-950 bg-blue-50/40 dark:bg-blue-950/20">
          <p className="text-[10px] font-semibold text-blue-700 dark:text-blue-400 uppercase tracking-wider">Scheduled</p>
          <p className="text-xl font-black text-blue-800 dark:text-blue-300 mt-0.5">{scheduledCount}</p>
        </div>
        <div className="p-3.5 rounded-xl border border-emerald-100 dark:border-emerald-950 bg-emerald-50/40 dark:bg-emerald-950/20">
          <p className="text-[10px] font-semibold text-emerald-700 dark:text-emerald-400 uppercase tracking-wider">Confirmed</p>
          <p className="text-xl font-black text-emerald-800 dark:text-emerald-300 mt-0.5">{confirmedCount}</p>
        </div>
        <div className="p-3.5 rounded-xl border border-teal-100 dark:border-teal-950 bg-teal-50/40 dark:bg-teal-950/20">
          <p className="text-[10px] font-semibold text-teal-700 dark:text-teal-400 uppercase tracking-wider">Completed</p>
          <p className="text-xl font-black text-teal-800 dark:text-teal-300 mt-0.5">{completedCount}</p>
        </div>
        <div className="p-3.5 rounded-xl border border-red-100 dark:border-red-950 bg-red-50/40 dark:bg-red-950/20">
          <p className="text-[10px] font-semibold text-red-700 dark:text-red-400 uppercase tracking-wider">Cancelled</p>
          <p className="text-xl font-black text-red-800 dark:text-red-300 mt-0.5">{cancelledCount}</p>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="p-4 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface)] flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
        <form onSubmit={handleSearchSubmit} className="flex-1 flex gap-2">
          <input
            type="text"
            placeholder="Search by customer name or notes..."
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

          {/* Org Filter */}
          <select
            value={selectedOrg}
            onChange={(e) => setSelectedOrg(e.target.value)}
            className="px-3 py-2 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-canvas)] text-xs text-[var(--color-text-main)] focus:outline-hidden"
          >
            <option value="">All Organizations</option>
            {organizations.map((org) => (
              <option key={org.id} value={org.id}>{org.name}</option>
            ))}
          </select>

          {/* Branch Filter */}
          <select
            value={selectedBranch}
            onChange={(e) => setSelectedBranch(e.target.value)}
            disabled={!selectedOrg}
            className="px-3 py-2 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-canvas)] text-xs text-[var(--color-text-main)] focus:outline-hidden disabled:opacity-50"
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
            <option value="SCHEDULED">Scheduled</option>
            <option value="CONFIRMED">Confirmed</option>
            <option value="COMPLETED">Completed</option>
            <option value="CANCELLED">Cancelled</option>
            <option value="NO_SHOW">No Show</option>
          </select>

          {(selectedOrg || selectedBranch || selectedStatus || selectedDate || searchTerm) && (
            <button
              onClick={() => {
                setSelectedOrg('');
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

      {/* Appointments Table */}
      <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface)] overflow-hidden shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-[var(--color-border-subtle)] bg-[var(--color-canvas)] text-[11px] font-semibold text-[var(--color-secondary)] uppercase tracking-wider">
                <th className="py-3 px-4">Booking Time</th>
                <th className="py-3 px-4">Customer</th>
                <th className="py-3 px-4">Organization & Branch</th>
                <th className="py-3 px-4">Service</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Notes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-border-subtle)] text-xs">
              {loading ? (
                <tr>
                  <td colSpan="6" className="py-8 text-center text-[var(--color-secondary)]">
                    Loading appointments directory...
                  </td>
                </tr>
              ) : appointments.length === 0 ? (
                <tr>
                  <td colSpan="6" className="py-8 text-center text-[var(--color-secondary)]">
                    No appointments found matching current filters.
                  </td>
                </tr>
              ) : (
                appointments.map((a) => {
                  const isScheduled = a.status === 'SCHEDULED';
                  const isConfirmed = a.status === 'CONFIRMED';
                  const isCompleted = a.status === 'COMPLETED';
                  const isCancelled = a.status === 'CANCELLED';

                  return (
                    <tr key={a.id} className="hover:bg-[var(--color-canvas)]/50 transition-colors">
                      <td className="py-3.5 px-4 font-mono">
                        <div className="font-bold text-[var(--color-text-main)]">
                          {a.appointment_date}
                        </div>
                        <div className="text-[11px] text-[var(--color-primary)]">
                          {a.appointment_time}
                        </div>
                      </td>
                      <td className="py-3.5 px-4 font-medium text-[var(--color-text-main)]">
                        {a.user_name || 'Guest User'}
                      </td>
                      <td className="py-3.5 px-4">
                        <div className="font-medium text-[var(--color-text-main)]">{a.organization_name}</div>
                        <div className="text-[11px] text-[var(--color-secondary)]">{a.branch_name}</div>
                      </td>
                      <td className="py-3.5 px-4 text-[var(--color-secondary)]">
                        {a.service_name || 'General Appointment'}
                      </td>
                      <td className="py-3.5 px-4">
                        <span
                          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold ${
                            isConfirmed
                              ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300'
                              : isScheduled
                              ? 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300'
                              : isCompleted
                              ? 'bg-teal-100 text-teal-800 dark:bg-teal-950 dark:text-teal-300'
                              : isCancelled
                              ? 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300'
                              : 'bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300'
                          }`}
                        >
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${
                              isConfirmed
                                ? 'bg-emerald-500'
                                : isScheduled
                                ? 'bg-blue-500'
                                : isCompleted
                                ? 'bg-teal-500'
                                : isCancelled
                                ? 'bg-red-500'
                                : 'bg-slate-400'
                            }`}
                          />
                          {a.status}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-[var(--color-secondary)] max-w-xs truncate">
                        {a.notes || '—'}
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
