import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';
import api from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import { useRealtimeQueue } from '../../hooks/useRealtimeQueue';

export default function StaffDashboard() {
  const { user } = useAuth();
  const [summary, setSummary] = useState(null);
  const [queueData, setQueueData] = useState(null);
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState('');
  const [actionMessage, setActionMessage] = useState(null);
  const isMountedRef = useRef(true);

  const loadStaffData = useCallback(async () => {
    try {
      setError('');
      const [sumRes, queueRes, apptRes] = await Promise.all([
        api.get('/api/staff/dashboard/summary'),
        api.get('/api/staff/queue'),
        api.get('/api/staff/appointments', { params: { limit: 5 } })
      ]);
      if (isMountedRef.current) {
        setSummary(sumRes.data);
        setQueueData(queueRes.data);
        setAppointments(apptRes.data);
      }
    } catch (err) {
      if (isMountedRef.current) {
        setError(err.response?.data?.detail || 'Failed to load staff dashboard');
      }
    } finally {
      if (isMountedRef.current) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    isMountedRef.current = true;
    loadStaffData();
    return () => {
      isMountedRef.current = false;
    };
  }, [loadStaffData]);

  // Real-time synchronization for staff queue board
  useRealtimeQueue({
    userId: user?.id,
    onTokenUpdate: useCallback(() => {
      loadStaffData();
    }, [loadStaffData]),
    onQueueRefresh: useCallback(() => {
      loadStaffData();
    }, [loadStaffData]),
  });

  const handleQueueAction = async (actionType, tokenId = null) => {
    if (actionLoading) return;
    setActionLoading(true);
    setActionMessage(null);
    setError('');

    try {
      let res;
      if (actionType === 'call-next') {
        const params = queueData?.assigned_counter?.id 
          ? { counter_id: queueData.assigned_counter.id } 
          : {};
        res = await api.post('/api/staff/queue/call-next', null, { params });
        setActionMessage({
          type: 'success',
          text: `Called token ${res.data.token_number} (${res.data.user_name || 'Customer'}) to ${queueData?.assigned_counter?.name || 'Counter'}`
        });
      } else if (actionType === 'start') {
        res = await api.post(`/api/staff/queue/${tokenId}/start`);
        setActionMessage({
          type: 'success',
          text: `Started serving token ${res.data.token_number}`
        });
      } else if (actionType === 'complete') {
        res = await api.post(`/api/staff/queue/${tokenId}/complete`);
        setActionMessage({
          type: 'success',
          text: `Successfully completed token ${res.data.token_number}. Counter is now available.`
        });
      } else if (actionType === 'skip') {
        res = await api.post(`/api/staff/queue/${tokenId}/skip`);
        setActionMessage({
          type: 'info',
          text: `Skipped token ${res.data.token_number}`
        });
      } else if (actionType === 'no-show') {
        res = await api.post(`/api/staff/queue/${tokenId}/no-show`);
        setActionMessage({
          type: 'info',
          text: `Marked token ${res.data.token_number} as No-Show`
        });
      }

      // Re-fetch queue data to guarantee database sync
      await loadStaffData();
    } catch (err) {
      const detail = err.response?.data?.detail || 'Operation failed. Please try again.';
      setError(typeof detail === 'string' ? detail : JSON.stringify(detail));
    } finally {
      if (isMountedRef.current) {
        setActionLoading(false);
      }
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[var(--color-primary)]"></div>
      </div>
    );
  }

  if (error && !queueData && !summary) {
    return (
      <div className="p-6 rounded-2xl border border-red-200 bg-red-50 text-red-700 text-xs">
        <p className="font-bold text-sm mb-1">Access Restricted</p>
        <p>{error}</p>
        <p className="mt-2 text-[11px] text-red-600">
          Note: Your user account must be registered and assigned as active staff to a branch.
        </p>
      </div>
    );
  }

  const currentToken = queueData?.current_token;
  const isServing = currentToken?.status === 'SERVING';
  const isCalled = currentToken?.status === 'CALLED';

  return (
    <div className="space-y-6">
      {/* Branch & Staff Identity Banner */}
      <div className="p-6 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border-subtle)] shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-teal-500/10 text-teal-600 dark:text-teal-400 font-bold text-2xl flex items-center justify-center border border-teal-500/20">
              🏢
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-teal-100 text-teal-800 dark:bg-teal-950 dark:text-teal-300">
                  {queueData?.organization_name || summary?.organization_name}
                </span>
                <span className="text-xs text-[var(--color-secondary)]">
                  • {queueData?.branch_city || summary?.branch_city}
                </span>
              </div>
              <h1 className="text-xl font-black text-[var(--color-text-main)] mt-1">
                {queueData?.branch_name || summary?.branch_name}
              </h1>
              <p className="text-xs text-[var(--color-secondary)] mt-0.5">
                Staff Operator: <strong className="text-[var(--color-text-main)]">{summary?.staff_name}</strong> ({summary?.staff_email})
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 bg-[var(--color-canvas)] p-3 rounded-xl border border-[var(--color-border-subtle)]">
            <div className="text-right">
              <p className="text-[10px] uppercase font-bold text-[var(--color-secondary)]">Assigned Station</p>
              <p className="text-sm font-black text-[var(--color-primary)]">
                {queueData?.assigned_counter 
                  ? `Counter #${queueData.assigned_counter.counter_number} (${queueData.assigned_counter.name})`
                  : (summary?.assigned_counter || 'Window Desk #1')}
              </p>
            </div>
            <div className="w-3 h-3 rounded-full bg-emerald-500 animate-pulse" title="Connected" />
          </div>
        </div>
      </div>

      {/* Action Notification / Error Banner */}
      {actionMessage && (
        <div className={`p-4 rounded-xl border flex items-center justify-between ${
          actionMessage.type === 'success' 
            ? 'bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300' 
            : 'bg-blue-50 dark:bg-blue-950/40 border-blue-200 dark:border-blue-800 text-blue-800 dark:text-blue-300'
        }`}>
          <div className="flex items-center gap-2 text-xs font-medium">
            <span>{actionMessage.type === 'success' ? '✓' : 'ℹ️'}</span>
            <span>{actionMessage.text}</span>
          </div>
          <button 
            type="button" 
            onClick={() => setActionMessage(null)}
            className="text-xs font-bold opacity-60 hover:opacity-100 cursor-pointer"
          >
            ✕
          </button>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 text-xs font-medium flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span>⚠️</span>
            <span>{error}</span>
          </div>
          <button 
            type="button" 
            onClick={() => setError('')}
            className="text-xs font-bold opacity-60 hover:opacity-100 cursor-pointer"
          >
            ✕
          </button>
        </div>
      )}

      {/* Real Queue Engine Operations Control Center */}
      <div className="p-6 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border-subtle)] shadow-md">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-5 border-b border-[var(--color-border-subtle)]">
          <div>
            <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--color-primary)]">
              Operational Command Console
            </span>
            <h2 className="text-lg font-black text-[var(--color-text-main)] mt-0.5">
              Active Desk Management
            </h2>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={loadStaffData}
              disabled={actionLoading}
              className="px-3 py-1.5 rounded-lg border border-[var(--color-border-subtle)] text-xs font-semibold text-[var(--color-secondary)] hover:text-[var(--color-text-main)] hover:bg-[var(--color-canvas)] transition-all flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
            >
              <span>↻</span>
              <span>Refresh Queue</span>
            </button>
          </div>
        </div>

        {/* Current Station Serving Card */}
        <div className="my-6 p-6 rounded-2xl bg-[var(--color-canvas)] border border-[var(--color-border-subtle)]">
          {currentToken ? (
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
              <div className="flex items-start sm:items-center gap-5">
                <div className="w-20 h-20 rounded-2xl bg-[var(--color-accent-subtle)] text-[var(--color-primary)] font-mono font-black text-2xl flex items-center justify-center border-2 border-[var(--color-primary)] shadow-sm">
                  {currentToken.token_number}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-extrabold uppercase tracking-wide ${
                      isServing 
                        ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 animate-pulse'
                        : 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300'
                    }`}>
                      ● {currentToken.status}
                    </span>
                    <span className="text-xs text-[var(--color-secondary)]">
                      Appt: {currentToken.appointment_time || 'Immediate'}
                    </span>
                  </div>
                  <h3 className="text-xl font-bold text-[var(--color-text-main)] mt-1">
                    {currentToken.user_name || 'Customer'}
                  </h3>
                  <p className="text-xs text-[var(--color-secondary)] mt-0.5">
                    Service: <strong className="text-[var(--color-text-main)]">{currentToken.service_name}</strong>
                  </p>
                </div>
              </div>

              {/* Action Buttons for Current Token */}
              <div className="flex flex-wrap items-center gap-2.5">
                {isCalled && (
                  <button
                    type="button"
                    onClick={() => handleQueueAction('start', currentToken.id)}
                    disabled={actionLoading}
                    className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold shadow-xs transition-all active:scale-95 disabled:opacity-50 disabled:pointer-events-none cursor-pointer flex items-center gap-1.5"
                  >
                    <span>▶</span>
                    <span>Start Serving</span>
                  </button>
                )}

                {isServing && (
                  <button
                    type="button"
                    onClick={() => handleQueueAction('complete', currentToken.id)}
                    disabled={actionLoading}
                    className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold shadow-xs transition-all active:scale-95 disabled:opacity-50 disabled:pointer-events-none cursor-pointer flex items-center gap-1.5"
                  >
                    <span>✓</span>
                    <span>Complete Service</span>
                  </button>
                )}

                {isCalled && (
                  <>
                    <button
                      type="button"
                      onClick={() => handleQueueAction('skip', currentToken.id)}
                      disabled={actionLoading}
                      className="px-4 py-2.5 bg-amber-600 hover:bg-amber-700 text-white rounded-xl text-xs font-bold shadow-xs transition-all active:scale-95 disabled:opacity-50 disabled:pointer-events-none cursor-pointer flex items-center gap-1.5"
                    >
                      <span>↷</span>
                      <span>Skip</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => handleQueueAction('no-show', currentToken.id)}
                      disabled={actionLoading}
                      className="px-4 py-2.5 bg-red-600 hover:bg-red-700 text-white rounded-xl text-xs font-bold shadow-xs transition-all active:scale-95 disabled:opacity-50 disabled:pointer-events-none cursor-pointer flex items-center gap-1.5"
                    >
                      <span>✕</span>
                      <span>Mark No-Show</span>
                    </button>
                  </>
                )}
              </div>
            </div>
          ) : (
            <div className="py-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-center sm:text-left">
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 rounded-2xl bg-gray-100 dark:bg-gray-800 text-[var(--color-secondary)] flex items-center justify-center text-2xl font-bold">
                  ☕
                </div>
                <div>
                  <h3 className="text-base font-bold text-[var(--color-text-main)]">
                    Desk Available — No Customer Currently Called
                  </h3>
                  <p className="text-xs text-[var(--color-secondary)] mt-0.5">
                    {queueData?.waiting_count > 0 
                      ? `${queueData.waiting_count} visitor(s) waiting in queue lobby.` 
                      : 'No waiting visitors in the lobby right now.'}
                  </p>
                </div>
              </div>

              <button
                type="button"
                onClick={() => handleQueueAction('call-next')}
                disabled={actionLoading || (queueData?.waiting_count ?? 0) === 0}
                className="w-full sm:w-auto px-6 py-3 bg-[var(--color-primary)] hover:opacity-90 text-white rounded-xl font-bold text-sm shadow-md transition-all active:scale-95 disabled:opacity-40 disabled:pointer-events-none cursor-pointer flex items-center justify-center gap-2"
              >
                <span>📢</span>
                <span>Call Next Customer</span>
              </button>
            </div>
          )}
        </div>

        {/* Real Metrics Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="p-4 rounded-xl bg-amber-50/60 dark:bg-amber-950/20 border border-amber-100 dark:border-amber-950/50 shadow-xs">
            <div className="flex items-center justify-between">
              <p className="text-xs font-bold text-amber-800 dark:text-amber-300 uppercase tracking-wider">Waiting in Queue</p>
              <span className="text-lg">⏳</span>
            </div>
            <p className="text-2xl font-black text-amber-900 dark:text-amber-200 mt-1">
              {queueData?.waiting_count ?? summary?.waiting_tokens ?? 0}
            </p>
            <p className="text-[11px] text-amber-700 dark:text-amber-400 mt-0.5">
              Eligible visitors in waiting lobby
            </p>
          </div>

          <div className="p-4 rounded-xl bg-blue-50/60 dark:bg-blue-950/20 border border-blue-100 dark:border-blue-950/50 shadow-xs">
            <div className="flex items-center justify-between">
              <p className="text-xs font-bold text-blue-800 dark:text-blue-300 uppercase tracking-wider">Serving / Active</p>
              <span className="text-lg">🎯</span>
            </div>
            <p className="text-2xl font-black text-blue-900 dark:text-blue-200 mt-1">
              {queueData?.today_serving_count ?? 0}
            </p>
            <p className="text-[11px] text-blue-700 dark:text-blue-400 mt-0.5">
              Tokens in Called or Serving state
            </p>
          </div>

          <div className="p-4 rounded-xl bg-teal-50/60 dark:bg-teal-950/20 border border-teal-100 dark:border-teal-950/50 shadow-xs">
            <div className="flex items-center justify-between">
              <p className="text-xs font-bold text-teal-800 dark:text-teal-300 uppercase tracking-wider">Completed Today</p>
              <span className="text-lg">✅</span>
            </div>
            <p className="text-2xl font-black text-teal-900 dark:text-teal-200 mt-1">
              {queueData?.today_completed_count ?? summary?.completed_today ?? 0}
            </p>
            <p className="text-[11px] text-teal-700 dark:text-teal-400 mt-0.5">
              Visitors serviced today
            </p>
          </div>
        </div>
      </div>

      {/* Two column preview: Next In Line vs Today's Appointments */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Next Waiting Tokens Stream */}
        <div className="rounded-2xl border border-[var(--color-border-subtle)] bg-[var(--color-surface)] p-5 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-bold text-[var(--color-text-main)]">Upcoming Waiting Stream</h2>
              <p className="text-[11px] text-[var(--color-secondary)]">Tokens queued for service in this branch</p>
            </div>
            <Link
              to="/staff/tokens"
              className="text-xs font-semibold text-[var(--color-primary)] hover:underline"
            >
              View All →
            </Link>
          </div>

          <div className="space-y-2">
            {!queueData?.waiting_tokens || queueData.waiting_tokens.length === 0 ? (
              <p className="text-xs text-[var(--color-secondary)] text-center py-8">
                No waiting tokens in lobby right now.
              </p>
            ) : (
              queueData.waiting_tokens.slice(0, 5).map((tok) => (
                <div
                  key={tok.id}
                  className="flex items-center justify-between p-3.5 rounded-xl bg-[var(--color-canvas)] border border-[var(--color-border-subtle)] text-xs hover:border-[var(--color-primary)] transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <span className="px-2.5 py-1 rounded-lg bg-[var(--color-accent-subtle)] text-[var(--color-primary)] font-mono font-bold">
                      {tok.token_number}
                    </span>
                    <div>
                      <p className="font-semibold text-[var(--color-text-main)]">
                        {tok.user_name || 'Customer'}
                      </p>
                      <p className="text-[10px] text-[var(--color-secondary)]">
                        {tok.service_name} • Appt: {tok.appointment_time || 'Standard'}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <div className="text-right mr-1">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300">
                        Pos #{tok.queue_position || '1'}
                      </span>
                      <p className="text-[10px] text-[var(--color-secondary)] mt-0.5">
                        ~{tok.estimated_waiting_time ?? 0}m wait
                      </p>
                    </div>

                    {/* Operational direct skip or no-show if needed */}
                    <button
                      type="button"
                      title="Skip token"
                      onClick={() => handleQueueAction('skip', tok.id)}
                      disabled={actionLoading}
                      className="p-1.5 text-xs text-amber-600 hover:bg-amber-100 dark:hover:bg-amber-950 rounded-lg transition-colors cursor-pointer disabled:opacity-50"
                    >
                      ↷
                    </button>
                    <button
                      type="button"
                      title="Mark as No-Show"
                      onClick={() => handleQueueAction('no-show', tok.id)}
                      disabled={actionLoading}
                      className="p-1.5 text-xs text-red-600 hover:bg-red-100 dark:hover:bg-red-950 rounded-lg transition-colors cursor-pointer disabled:opacity-50"
                    >
                      ✕
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Today's Schedule */}
        <div className="rounded-2xl border border-[var(--color-border-subtle)] bg-[var(--color-surface)] p-5 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-bold text-[var(--color-text-main)]">Today's Appointments</h2>
              <p className="text-[11px] text-[var(--color-secondary)]">Upcoming visitor bookings</p>
            </div>
            <Link
              to="/staff/appointments"
              className="text-xs font-semibold text-[var(--color-primary)] hover:underline"
            >
              View All →
            </Link>
          </div>

          <div className="space-y-2">
            {appointments.length === 0 ? (
              <p className="text-xs text-[var(--color-secondary)] text-center py-8">
                No appointments booked for this branch today.
              </p>
            ) : (
              appointments.slice(0, 5).map((apt) => (
                <div
                  key={apt.id}
                  className="flex items-center justify-between p-3.5 rounded-xl bg-[var(--color-canvas)] border border-[var(--color-border-subtle)] text-xs"
                >
                  <div className="flex items-center gap-3">
                    <div className="font-mono text-center">
                      <p className="font-bold text-[var(--color-primary)]">{apt.appointment_time}</p>
                    </div>
                    <div>
                      <p className="font-semibold text-[var(--color-text-main)]">{apt.user_name || 'Guest User'}</p>
                      <p className="text-[10px] text-[var(--color-secondary)]">{apt.service_name}</p>
                    </div>
                  </div>
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                    apt.status === 'COMPLETED' 
                      ? 'bg-teal-100 text-teal-800 dark:bg-teal-950 dark:text-teal-300'
                      : apt.status === 'CANCELLED'
                        ? 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300'
                        : 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300'
                  }`}>
                    {apt.status}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
