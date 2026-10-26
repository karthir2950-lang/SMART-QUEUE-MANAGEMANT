import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';
import api, { supabase } from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import { useRealtimeQueue } from '../../hooks/useRealtimeQueue';

import { isAppointmentValidAndUpcoming } from '../../utils/appointmentUtils';

export { isAppointmentValidAndUpcoming };

export default function MyAppointments() {
  const { user } = useAuth();
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [cancellingId, setCancellingId] = useState(null);

  const [confirmAppt, setConfirmAppt] = useState(null);

  const abortControllerRef = useRef(null);

  const fetchAppointments = useCallback(async () => {
    // Abort previous in-flight request if any
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setLoading(true);
    setError('');

    try {
      const res = await api.get('/api/appointments/user', {
        signal: controller.signal,
      });
      if (!controller.signal.aborted) {
        const rawList = Array.isArray(res.data) ? res.data : [];
        const activeList = rawList.filter(isAppointmentValidAndUpcoming);
        setAppointments(activeList);
        setError('');
        setLoading(false);
      }
    } catch (err) {
      if (controller.signal.aborted || err.name === 'CanceledError' || err.code === 'ERR_CANCELED') {
        return;
      }
      // If backend is offline or unreachable, try fetching directly from Supabase
      if (!err.response) {
        try {
          const { data: { session } } = await supabase.auth.getSession();
          if (session?.user?.id) {
            const { data: sbData, error: sbErr } = await supabase
              .from('appointments')
              .select('*, service:services(*), branch:branches(*)')
              .eq('customer_id', session.user.id)
              .eq('status', 'BOOKED')
              .order('appointment_time', { ascending: true });

            if (!sbErr && Array.isArray(sbData)) {
              const activeList = sbData.filter(isAppointmentValidAndUpcoming);
              setAppointments(activeList);
              setError('');
              setLoading(false);
              return;
            }
          }
        } catch {
          // ignore
        }
      }

      const errorDetail = err.response?.data?.detail;
      const safeMessage = typeof errorDetail === 'string'
        ? errorDetail
        : 'Failed to load appointments. Please check your connection and try again.';
      setError(safeMessage);
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAppointments();
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [fetchAppointments]);

  // Phase 4: Dynamic Auto-Removal Timer
  // If an appointment's scheduled time passes while the page remains open,
  // remove it automatically without requiring a manual refresh.
  // Cleans up on unmount and avoids unnecessary rerenders.
  useEffect(() => {
    const timerId = setInterval(() => {
      setAppointments((prev) => {
        const validList = prev.filter(isAppointmentValidAndUpcoming);
        if (validList.length !== prev.length) {
          return validList;
        }
        return prev;
      });
    }, 5000);

    return () => clearInterval(timerId);
  }, []);

  // Real-time synchronization for appointment and queue updates
  useRealtimeQueue({
    userId: user?.id,
    onAppointmentUpdate: useCallback((updatedAppt) => {
      if (!updatedAppt || !updatedAppt.id) return;
      if (updatedAppt.status !== 'BOOKED' || !isAppointmentValidAndUpcoming(updatedAppt)) {
        setAppointments((prev) => prev.filter((a) => a.id !== updatedAppt.id));
      } else {
        setAppointments((prev) =>
          prev.map((a) => (a.id === updatedAppt.id ? { ...a, ...updatedAppt } : a))
        );
      }
    }, []),
    onTokenUpdate: useCallback((token) => {
      if (!token) return;
      if (['COMPLETED', 'CANCELLED', 'NO_SHOW', 'SKIPPED'].includes(token.status)) {
        setAppointments((prev) =>
          prev.filter((a) => a.id !== token.appointment_id && a.queue_token_id !== (token.id || token.token_id))
        );
        return;
      }
      setAppointments((prev) =>
        prev.map((a) => {
          if (a.id === token.appointment_id || a.queue_token_id === token.id) {
            return {
              ...a,
              status: token.status || a.status,
              queue_position: token.queue_position !== undefined ? token.queue_position : a.queue_position,
              estimated_waiting_time: token.estimated_waiting_time !== undefined ? token.estimated_waiting_time : a.estimated_waiting_time,
            };
          }
          return a;
        })
      );
    }, []),
    onQueueRefresh: useCallback(() => {
      fetchAppointments();
    }, [fetchAppointments]),
  });

  const handleOpenCancelModal = (appointment) => {
    if (cancellingId) return; // Prevent duplicate cancel submissions
    setError('');
    setConfirmAppt(appointment);
  };

  const executeCancel = async (id) => {
    if (cancellingId) return; // Prevent duplicate cancel submissions
    setCancellingId(id);
    setError('');
    setSuccessMessage('');
    try {
      const res = await api.post(`/api/appointments/${id}/cancel`);
      // Immediately remove the cancelled appointment from displayed list
      setAppointments((prev) => prev.filter((a) => a.id !== id));
      // Show success message only after backend confirms cancellation
      setSuccessMessage(res.data?.message || 'Appointment cancelled successfully');
      setConfirmAppt(null);
      // Refetch from backend to guarantee fresh synchronization
      await fetchAppointments();
    } catch (err) {
      const detail = err.response?.data?.detail;
      const msg = typeof detail === 'string' ? detail : 'Failed to cancel appointment. Please try again.';
      setError(msg);
      setConfirmAppt(null);
    } finally {
      setCancellingId(null);
    }
  };

  return (
    <div className="max-w-4xl mx-auto pb-12">
      <div className="mb-8">
        <span className="text-xs font-bold uppercase tracking-widest text-[var(--color-primary)]">
          Queue History
        </span>
        <h1 className="text-3xl font-bold tracking-tight text-[var(--color-text-main)] mt-1">
          My Appointments
        </h1>
        <p className="text-[var(--color-secondary)] mt-1 text-sm">
          Track active queue tokens, view details, and manage appointments.
        </p>
      </div>

      {successMessage && (
        <div className="p-4 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-900/60 text-emerald-700 dark:text-emerald-400 text-sm font-medium mb-6 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span>✅</span>
            <span>{successMessage}</span>
          </div>
          <button
            type="button"
            onClick={() => setSuccessMessage('')}
            className="text-emerald-700 dark:text-emerald-400 hover:opacity-75 font-bold cursor-pointer"
          >
            ✕
          </button>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900/60 text-red-700 dark:text-red-400 text-sm font-medium mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-center gap-2">
            <span>⚠️</span>
            <span>{error}</span>
          </div>
          <button
            type="button"
            onClick={fetchAppointments}
            disabled={loading}
            className="self-start sm:self-auto px-4 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded-xl text-xs font-bold transition-colors disabled:opacity-50 cursor-pointer shadow-xs"
          >
            {loading ? 'Retrying...' : 'Retry'}
          </button>
        </div>
      )}

      <div className="space-y-4">
        {loading && (
          <div className="p-12 text-center text-[var(--color-secondary)]">
            <div className="w-8 h-8 border-3 border-[var(--color-primary)] border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
            <p className="text-sm font-medium">Loading your appointments...</p>
          </div>
        )}

        {!loading && !error && appointments.length === 0 && (
          <div className="bg-[var(--color-surface)] p-10 rounded-[22px] border border-[var(--color-border-subtle)] text-center text-[var(--color-secondary)] shadow-xs">
            <p className="font-bold text-base text-[var(--color-text-main)] mb-1">
              You don't have any upcoming booked appointments.
            </p>
            <p className="text-xs mb-6">
              Choose a sector in the application hub to schedule your visit.
            </p>
            <Link
              to="/user/dashboard"
              className="inline-flex px-5 py-2.5 bg-[var(--color-primary)] text-white text-xs font-bold uppercase tracking-wider rounded-xl hover:opacity-90 transition-opacity"
            >
              Book a Service →
            </Link>
          </div>
        )}

        {!loading && !error &&
          appointments.map((app) => (
            <div
              key={app.id}
              className="bg-[var(--color-surface)] p-6 rounded-[20px] border border-[var(--color-border-subtle)] shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-5 transition-colors"
            >
              <div className="flex-1 min-w-0">
                <div className="flex flex-wrap items-center gap-2.5 mb-2.5">
                  <span
                    className={`px-3 py-1 text-[10px] font-bold uppercase rounded-full tracking-wider ${
                      app.status === 'BOOKED'
                        ? 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300'
                        : app.status === 'CANCELLED'
                        ? 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300'
                        : 'bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-300'
                    }`}
                  >
                    {app.status}
                  </span>

                  {app.token_number ? (
                    <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold bg-indigo-50 dark:bg-indigo-950/70 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800/80 font-mono shadow-2xs">
                      <span>🎫</span>
                      <span>Token: {app.token_number}</span>
                    </span>
                  ) : (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-medium bg-slate-100 dark:bg-slate-800 text-slate-500 italic">
                      No Token
                    </span>
                  )}

                  <span className="text-xs font-semibold text-[var(--color-secondary)]">
                    📅 {app.appointment_date} • 🕒 {app.appointment_time}
                  </span>
                </div>

                <h3 className="text-xl font-bold text-[var(--color-text-main)] truncate">
                  {app.service_name}
                </h3>
                <p className="text-xs text-[var(--color-secondary)] mt-1">
                  🏢 {app.organization_name} • 📍 {app.branch_name}
                </p>

                {app.status === 'BOOKED' && (app.queue_position != null || app.estimated_waiting_time != null) && (
                  <div className="mt-2.5 flex items-center gap-4 text-xs font-medium text-[var(--color-secondary)]">
                    {app.queue_position != null && (
                      <span className="inline-flex items-center gap-1">
                        <span>👥</span> Position #{app.queue_position}
                      </span>
                    )}
                    {app.estimated_waiting_time != null && (
                      <span className="inline-flex items-center gap-1">
                        <span>⏱️</span> ~{app.estimated_waiting_time} min wait
                      </span>
                    )}
                  </div>
                )}
              </div>

              <div className="flex items-center gap-2 pt-3 md:pt-0 border-t md:border-t-0 border-[var(--color-border-subtle)] shrink-0">
                {app.status === 'BOOKED' && (
                  <>
                    <Link
                      to={`/user/token/${app.id}`}
                      className="px-4 py-2.5 bg-[var(--color-primary)] hover:opacity-90 text-white text-xs font-bold rounded-xl transition-all shadow-xs inline-flex items-center gap-1.5"
                    >
                      <span>🎫</span>
                      <span>View Token</span>
                    </Link>
                    <button
                      type="button"
                      id={`cancel-btn-${app.id}`}
                      onClick={() => handleOpenCancelModal(app)}
                      disabled={Boolean(cancellingId)}
                      className="px-4 py-2.5 border border-red-200 dark:border-red-900/60 text-red-600 dark:text-red-400 text-xs font-bold rounded-xl hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors disabled:opacity-50 cursor-pointer"
                    >
                      Cancel
                    </button>
                  </>
                )}
                {app.status !== 'BOOKED' && (
                  <span className="text-xs text-[var(--color-secondary)] italic">
                    Appointment {app.status.toLowerCase()}
                  </span>
                )}
              </div>
            </div>
          ))}
      </div>

      {/* Cancellation Confirmation Modal */}
      {confirmAppt && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="w-full max-w-md rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border-subtle)] shadow-2xl p-6">
            <div className="flex items-center justify-between pb-3 border-b border-[var(--color-border-subtle)]">
              <div className="flex items-center gap-2 text-red-600 dark:text-red-400">
                <span className="text-lg">⚠️</span>
                <h3 className="text-base font-bold text-[var(--color-text-main)]">
                  Cancel Appointment
                </h3>
              </div>
              <button
                type="button"
                id="close-cancel-modal-btn"
                onClick={() => setConfirmAppt(null)}
                disabled={Boolean(cancellingId)}
                className="text-[var(--color-secondary)] hover:text-[var(--color-text-main)] text-sm cursor-pointer disabled:opacity-50"
              >
                ✕
              </button>
            </div>

            <div className="mt-4 space-y-2 text-sm text-[var(--color-secondary)]">
              <p>
                Are you sure you want to cancel your appointment for{' '}
                <strong className="text-[var(--color-text-main)]">{confirmAppt.service_name}</strong>?
              </p>
              <div className="p-3 rounded-xl bg-[var(--color-canvas)] border border-[var(--color-border-subtle)] text-xs space-y-1">
                <div>🏢 <span className="font-medium text-[var(--color-text-main)]">{confirmAppt.organization_name}</span></div>
                <div>📍 <span className="text-[var(--color-text-main)]">{confirmAppt.branch_name}</span></div>
                <div>📅 {confirmAppt.appointment_date} • 🕒 {confirmAppt.appointment_time}</div>
                {confirmAppt.token_number && (
                  <div className="font-mono font-bold text-[var(--color-primary)]">🎫 Token: {confirmAppt.token_number}</div>
                )}
              </div>
              <p className="text-xs text-red-500 font-medium pt-1">
                This action cannot be undone. Your queue token will be released.
              </p>
            </div>

            <div className="mt-6 flex items-center justify-end gap-3 pt-3 border-t border-[var(--color-border-subtle)]">
              <button
                type="button"
                id="cancel-modal-back-btn"
                onClick={() => setConfirmAppt(null)}
                disabled={Boolean(cancellingId)}
                className="px-4 py-2 rounded-xl text-xs font-bold text-[var(--color-text-main)] hover:bg-[var(--color-canvas)] border border-[var(--color-border-subtle)] transition-colors cursor-pointer disabled:opacity-50"
              >
                Keep Appointment
              </button>
              <button
                type="button"
                id="confirm-cancel-appt-btn"
                onClick={() => executeCancel(confirmAppt.id)}
                disabled={Boolean(cancellingId)}
                className="px-4 py-2 rounded-xl text-xs font-bold bg-red-600 hover:bg-red-700 text-white transition-colors cursor-pointer disabled:opacity-50 shadow-xs flex items-center gap-1.5"
              >
                {cancellingId === confirmAppt.id ? (
                  <>
                    <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                    <span>Cancelling...</span>
                  </>
                ) : (
                  <span>Yes, Cancel</span>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
