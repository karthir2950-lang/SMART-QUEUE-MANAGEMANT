import React, { useState, useEffect } from 'react';
import api from '../../services/api';

export default function StaffAppointments() {
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Filters
  const [selectedStatus, setSelectedStatus] = useState('');
  const [selectedDate, setSelectedDate] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  const loadAppointments = async () => {
    try {
      setLoading(true);
      setError('');
      const res = await api.get('/api/staff/appointments', {
        params: {
          status: selectedStatus || undefined,
          date: selectedDate || undefined,
          search: searchTerm || undefined
        }
      });
      setAppointments(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load branch appointments');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAppointments();
  }, [selectedStatus, selectedDate]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    loadAppointments();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--color-text-main)]">
            Branch Appointments
          </h1>
          <p className="text-xs text-[var(--color-secondary)] mt-1">
            Customer bookings scheduled for your assigned branch station (Read-Only)
          </p>
        </div>
        <button
          onClick={loadAppointments}
          className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface)] text-xs font-semibold text-[var(--color-text-main)] hover:bg-[var(--color-surface-hover)] shadow-xs"
        >
          <span>🔄</span>
          <span>Refresh</span>
        </button>
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
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="px-3 py-2 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-canvas)] text-xs text-[var(--color-text-main)] focus:outline-hidden"
          />

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

          {(selectedStatus || selectedDate || searchTerm) && (
            <button
              onClick={() => {
                setSelectedStatus('');
                setSelectedDate('');
                setSearchTerm('');
                setTimeout(loadAppointments, 0);
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
                <th className="py-3 px-4">Time</th>
                <th className="py-3 px-4">Date</th>
                <th className="py-3 px-4">Customer</th>
                <th className="py-3 px-4">Service</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Notes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-border-subtle)] text-xs">
              {loading ? (
                <tr>
                  <td colSpan="6" className="py-8 text-center text-[var(--color-secondary)]">
                    Loading branch appointments...
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
                  const isConfirmed = a.status === 'CONFIRMED';
                  const isScheduled = a.status === 'SCHEDULED';
                  const isCompleted = a.status === 'COMPLETED';
                  const isCancelled = a.status === 'CANCELLED';

                  return (
                    <tr key={a.id} className="hover:bg-[var(--color-canvas)]/50 transition-colors">
                      <td className="py-3.5 px-4 font-mono font-bold text-[var(--color-primary)]">
                        {a.appointment_time}
                      </td>
                      <td className="py-3.5 px-4 text-[var(--color-secondary)]">
                        {a.appointment_date}
                      </td>
                      <td className="py-3.5 px-4 font-medium text-[var(--color-text-main)]">
                        {a.user_name || 'Guest User'}
                      </td>
                      <td className="py-3.5 px-4 text-[var(--color-secondary)]">
                        {a.service_name || 'General Service'}
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
