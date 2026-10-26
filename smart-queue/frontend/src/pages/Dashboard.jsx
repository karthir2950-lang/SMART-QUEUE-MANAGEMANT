import React, { useEffect, useState, useCallback, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import api from '../services/api';
import queueService from '../services/queueService';
import { useAuth } from '../context/AuthContext';
import { useRealtimeQueue } from '../hooks/useRealtimeQueue';

export default function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [sectors, setSectors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [navigatingSlug, setNavigatingSlug] = useState(null);
  const [activeQueue, setActiveQueue] = useState(null);
  const [queueLoading, setQueueLoading] = useState(false);
  const [lastQueueSync, setLastQueueSync] = useState(null);
  const isMountedRef = useRef(true);

  const fetchSectors = useCallback(async (signal) => {
    setLoading(true);
    setError('');
    try {
      const response = await api.get('/api/sectors', signal ? { signal } : {});
      if (isMountedRef.current) {
        // Exactly the 6 standard active sectors from database
        const activeSectors = (response.data || []).filter(s => !s.status || s.status === 'ACTIVE');
        setSectors(activeSectors);
      }
    } catch (err) {
      if (signal?.aborted || err.name === 'CanceledError' || err.code === 'ERR_CANCELED') {
        return;
      }
      if (isMountedRef.current) {
        const errorDetail = err.response?.data?.detail;
        const msg = typeof errorDetail === 'string'
          ? errorDetail
          : (err.message && !err.response)
            ? 'Unable to connect to the backend server. Please verify the service is running.'
            : 'Failed to load sectors. Please try again.';
        setError(msg);
      }
    } finally {
      if (isMountedRef.current && !signal?.aborted) {
        setLoading(false);
      }
    }
  }, []);

  const fetchActiveQueue = useCallback(async () => {
    if (!user) return;
    try {
      setQueueLoading(true);
      const res = await queueService.getActiveToken();
      if (isMountedRef.current) {
        if (res && res.token_number && !['COMPLETED', 'CANCELLED'].includes(res.status)) {
          setActiveQueue(res);
          setLastQueueSync(new Date());
        } else {
          setActiveQueue(null);
        }
      }
    } catch {
      if (isMountedRef.current) setActiveQueue(null);
    } finally {
      if (isMountedRef.current) setQueueLoading(false);
    }
  }, [user]);

  useEffect(() => {
    isMountedRef.current = true;
    const controller = new AbortController();
    fetchSectors(controller.signal);
    fetchActiveQueue();
    return () => {
      isMountedRef.current = false;
      controller.abort();
    };
  }, [fetchSectors, fetchActiveQueue]);

  // Real-time queue monitor subscription for authenticated user
  const { connectionState } = useRealtimeQueue({
    userId: user?.id,
    onTokenUpdate: useCallback((token) => {
      if (!token) return;
      if (token.status === 'COMPLETED' || token.status === 'CANCELLED') {
        setActiveQueue(null);
      } else {
        fetchActiveQueue();
      }
    }, [fetchActiveQueue]),
    onAppointmentUpdate: useCallback((appt) => {
      if (appt && (appt.status === 'COMPLETED' || appt.status === 'CANCELLED')) {
        setActiveQueue(null);
      } else {
        fetchActiveQueue();
      }
    }, [fetchActiveQueue]),
    onQueueRefresh: useCallback(() => {
      fetchActiveQueue();
    }, [fetchActiveQueue]),
  });

  const getSectorIcon = (name = '') => {
    const lower = name.toLowerCase();
    if (lower.includes('hospital')) return '🏥';
    if (lower.includes('bank')) return '🏦';
    if (lower.includes('restaurant')) return '🍽️';
    if (lower.includes('government')) return '🏛️';
    if (lower.includes('retail')) return '🛍️';
    if (lower.includes('supermarket')) return '🛒';
    return '🏢';
  };

  const getSectorDescription = (sector) => {
    if (sector.description && sector.description.trim().length > 0) {
      return sector.description;
    }
    const lower = sector.name.toLowerCase();
    if (lower.includes('hospital')) return 'Medical and healthcare services';
    if (lower.includes('bank')) return 'Banking and financial services';
    if (lower.includes('restaurant')) return 'Table reservation and dining services';
    if (lower.includes('government')) return 'Public administration and citizen services';
    if (lower.includes('retail')) return 'Store customer assistance and checkout';
    if (lower.includes('supermarket')) return 'Grocery express counter and support';
    return 'Queue and appointment services';
  };

  const handleSelectSector = (sector) => {
    // Single-click protection & action locking
    if (navigatingSlug) return;
    setNavigatingSlug(sector.slug);
    navigate(`/sector/${sector.slug}`);
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Real-Time Live Queue Monitor Card (When user has an active token) */}
      {activeQueue && (
        <div className="p-6 rounded-[24px] bg-gradient-to-br from-[var(--color-surface)] via-[var(--color-surface)] to-[var(--color-accent-subtle)]/40 border border-[var(--color-border-subtle)] shadow-md">
          <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-[var(--color-border-subtle)]">
            <div className="flex items-center gap-2.5">
              <span className="text-xl">⚡</span>
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--color-primary)]">
                  Live Queue Monitor
                </span>
                <h2 className="text-sm font-bold text-[var(--color-text-main)]">
                  {activeQueue.branch_name} • {activeQueue.service_name}
                </h2>
              </div>
            </div>

            <div className="flex items-center gap-2.5">
              <span
                className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold tracking-wide border transition-colors ${
                  connectionState === 'Live'
                    ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-400 border-emerald-300 dark:border-emerald-800'
                    : connectionState === 'Reconnecting'
                    ? 'bg-amber-50 text-amber-700 dark:bg-amber-950/60 dark:text-amber-400 border-amber-300 dark:border-amber-800'
                    : 'bg-red-50 text-red-700 dark:bg-red-950/60 dark:text-red-400 border-red-300 dark:border-red-800'
                }`}
              >
                <span
                  className={`w-2 h-2 rounded-full ${
                    connectionState === 'Live'
                      ? 'bg-emerald-500 animate-pulse'
                      : connectionState === 'Reconnecting'
                      ? 'bg-amber-500 animate-spin'
                      : 'bg-red-500'
                  }`}
                ></span>
                <span>{connectionState}</span>
              </span>

              {lastQueueSync && (
                <span className="text-[11px] text-[var(--color-secondary)]">
                  {lastQueueSync.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </span>
              )}

              <button
                type="button"
                onClick={fetchActiveQueue}
                disabled={queueLoading}
                className="px-2.5 py-1 text-xs font-semibold text-[var(--color-secondary)] hover:text-[var(--color-text-main)] hover:bg-[var(--color-canvas)] border border-[var(--color-border-subtle)] rounded-lg flex items-center gap-1 cursor-pointer disabled:opacity-50"
                title="Refresh active queue status"
              >
                <span>🔄</span>
                <span>Sync</span>
              </button>
            </div>
          </div>

          <div className="mt-5 grid grid-cols-1 sm:grid-cols-4 gap-4 items-center">
            {/* Token Badge */}
            <div className="p-4 rounded-2xl bg-[var(--color-canvas)] border border-[var(--color-border-subtle)] text-center sm:text-left flex sm:flex-col items-center sm:items-start justify-between">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--color-secondary)]">
                  Your Token
                </span>
                <p className="text-3xl font-black text-[var(--color-primary)] font-mono">
                  {activeQueue.token_number}
                </p>
              </div>
              <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-extrabold uppercase mt-1 ${
                activeQueue.status === 'CALLED'
                  ? 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300 animate-pulse'
                  : activeQueue.status === 'SERVING'
                  ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300'
                  : 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300'
              }`}>
                ● {activeQueue.status}
              </span>
            </div>

            {/* Now Serving */}
            <div className="p-4 rounded-2xl bg-[var(--color-canvas)] border border-[var(--color-border-subtle)] text-center sm:text-left">
              <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--color-secondary)]">
                Currently Serving
              </span>
              <p className="text-xl font-bold text-[var(--color-text-main)] mt-1 truncate">
                {activeQueue.currently_serving_token ? (
                  <span className="font-mono text-emerald-600 dark:text-emerald-400">
                    {activeQueue.currently_serving_token}
                  </span>
                ) : (
                  <span className="text-xs text-[var(--color-secondary)] italic">Awaiting call</span>
                )}
              </p>
              <p className="text-[10px] text-[var(--color-secondary)] mt-0.5 truncate">
                {activeQueue.currently_serving_counter || 'Service Desk'}
              </p>
            </div>

            {/* People Ahead & Wait */}
            <div className="p-4 rounded-2xl bg-[var(--color-canvas)] border border-[var(--color-border-subtle)] text-center sm:text-left">
              <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--color-secondary)]">
                Queue Position & Wait
              </span>
              <p className="text-xl font-bold text-[var(--color-text-main)] mt-1">
                {activeQueue.status === 'WAITING' ? (
                  activeQueue.people_ahead === 0 ? (
                    <span className="text-emerald-600 dark:text-emerald-400 text-sm font-bold">You are next!</span>
                  ) : (
                    <span>{activeQueue.people_ahead} ahead</span>
                  )
                ) : activeQueue.status === 'CALLED' ? (
                  <span className="text-amber-500 text-sm font-bold animate-pulse">Proceed to desk</span>
                ) : (
                  <span>Being served</span>
                )}
              </p>
              <p className="text-[10px] text-[var(--color-secondary)] mt-0.5">
                {activeQueue.estimated_waiting_time != null
                  ? `~${activeQueue.estimated_waiting_time} min wait`
                  : 'Estimated wait unavailable'}
              </p>
            </div>

            {/* View Pass Action */}
            <div className="flex sm:flex-col justify-center items-stretch gap-2">
              <Link
                to={`/user/token/${activeQueue.appointment_id}`}
                className="w-full px-4 py-3 bg-[var(--color-primary)] hover:opacity-90 text-white text-xs font-bold rounded-xl transition-all shadow-xs text-center flex items-center justify-center gap-1.5"
              >
                <span>🎫</span>
                <span>View Digital Pass →</span>
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Header / Hub Intro */}
      <div className="mb-8">
        <span className="text-xs font-bold uppercase tracking-widest text-[var(--color-primary)]">
          Sector Application Hub
        </span>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight text-[var(--color-text-main)] mt-1">
          Choose a Service
        </h1>
        <p className="text-[var(--color-secondary)] mt-2 text-sm sm:text-base">
          Select your destination sector to view verified organizations, branches, and book queue tokens.
        </p>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-4 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900/60 text-red-700 dark:text-red-400 text-sm font-medium mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="text-base">⚠️</span>
            <span>{error}</span>
          </div>
          <button
            type="button"
            onClick={() => fetchSectors()}
            className="self-start sm:self-auto px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-xl text-xs font-semibold transition-all shadow-xs active:scale-95 cursor-pointer flex items-center gap-1.5"
          >
            <span>↻</span>
            <span>Retry</span>
          </button>
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="bg-[var(--color-surface)] p-6 rounded-[20px] border border-[var(--color-border-subtle)] animate-pulse">
              <div className="w-14 h-14 rounded-2xl bg-gray-200 dark:bg-gray-700 mb-4"></div>
              <div className="h-5 bg-gray-200 dark:bg-gray-700 rounded w-1/2 mb-2"></div>
              <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-4"></div>
              <div className="h-9 bg-gray-200 dark:bg-gray-700 rounded-xl w-full"></div>
            </div>
          ))}
        </div>
      )}

      {/* Sector Cards Grid */}
      {!loading && !error && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {sectors.map((sector) => {
            const isTargetNavigating = navigatingSlug === sector.slug;
            return (
              <div
                key={sector.id}
                role="button"
                tabIndex={0}
                onClick={() => handleSelectSector(sector)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    handleSelectSector(sector);
                  }
                }}
                className={`bg-[var(--color-surface)] p-6 rounded-[20px] border border-[var(--color-border-subtle)] hover:border-[var(--color-primary)] shadow-xs hover:shadow-md transition-all flex flex-col justify-between group cursor-pointer ${
                  navigatingSlug ? 'pointer-events-none' : ''
                }`}
              >
                <div>
                  <div className="w-14 h-14 rounded-2xl bg-[var(--color-accent-subtle)] text-[var(--color-primary)] flex items-center justify-center text-3xl mb-4 group-hover:scale-105 transition-transform">
                    {getSectorIcon(sector.name)}
                  </div>
                  <h2 className="text-xl font-bold text-[var(--color-text-main)] mb-1">
                    {sector.name}
                  </h2>
                  <p className="text-sm text-[var(--color-secondary)] line-clamp-2 leading-relaxed">
                    {getSectorDescription(sector)}
                  </p>
                </div>

                <div className="mt-6 pt-4 border-t border-[var(--color-border-subtle)]">
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleSelectSector(sector);
                    }}
                    disabled={Boolean(navigatingSlug)}
                    className="w-full py-2.5 px-4 bg-[var(--color-accent-subtle)] hover:bg-[var(--color-primary)] text-[var(--color-primary)] hover:text-white rounded-xl font-semibold text-sm transition-all flex items-center justify-center gap-2 group-hover:bg-[var(--color-primary)] group-hover:text-white disabled:opacity-50 disabled:pointer-events-none cursor-pointer"
                  >
                    <span>{isTargetNavigating ? 'Opening...' : 'View Services'}</span>
                    {!isTargetNavigating && <span>→</span>}
                  </button>
                </div>
              </div>
            );
          })}

          {sectors.length === 0 && (
            <div className="col-span-full bg-[var(--color-surface)] p-12 rounded-[20px] border border-[var(--color-border-subtle)] text-center text-[var(--color-secondary)]">
              No active sectors found in the database.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
