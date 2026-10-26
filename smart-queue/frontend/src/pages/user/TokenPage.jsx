import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { QRCodeSVG } from 'qrcode.react';
import api from '../../services/api';
import queueService from '../../services/queueService';
import { useAuth } from '../../context/AuthContext';
import { useRealtimeQueue } from '../../hooks/useRealtimeQueue';

export default function TokenPage() {
  const { appointmentId } = useParams();
  const { user } = useAuth();
  const [token, setToken] = useState(null);
  const [prediction, setPrediction] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(new Date());
  const prevStatusRef = useRef(null);

  const playChime = useCallback(() => {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      const osc1 = ctx.createOscillator();
      const osc2 = ctx.createOscillator();
      const gain = ctx.createGain();

      osc1.type = 'sine';
      osc1.frequency.setValueAtTime(587.33, ctx.currentTime); // D5
      osc2.type = 'sine';
      osc2.frequency.setValueAtTime(880, ctx.currentTime + 0.18); // A5

      gain.gain.setValueAtTime(0.25, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.85);

      osc1.connect(gain);
      osc2.connect(gain);
      gain.connect(ctx.destination);

      osc1.start(ctx.currentTime);
      osc1.stop(ctx.currentTime + 0.18);
      osc2.start(ctx.currentTime + 0.18);
      osc2.stop(ctx.currentTime + 0.85);
    } catch {
      // Audio playback might require initial user touch gesture
    }
  }, []);

  const fetchTokenAndPrediction = useCallback(async (isInitial = false) => {
    try {
      if (isInitial) setLoading(true);
      const [tokenRes, predRes] = await Promise.allSettled([
        queueService.getToken(appointmentId),
        queueService.getPrediction(appointmentId)
      ]);

      if (tokenRes.status === 'fulfilled' && tokenRes.value) {
        const nextToken = tokenRes.value.data || tokenRes.value;
        if (nextToken && (nextToken.token_number || nextToken.id)) {
          // Check if transition to CALLED just happened -> sound chime
          if (prevStatusRef.current && prevStatusRef.current !== 'CALLED' && nextToken.status === 'CALLED') {
            playChime();
          }
          prevStatusRef.current = nextToken.status;
          setToken(nextToken);
          setError('');
        } else {
          if (isInitial) setError('Failed to load token details.');
        }
      } else {
        const errDetail = tokenRes.reason?.response?.data?.detail;
        if (isInitial) setError(typeof errDetail === 'string' ? errDetail : 'Failed to load token details.');
      }

      if (predRes.status === 'fulfilled' && predRes.value) {
        const nextPred = predRes.value.data || predRes.value;
        if (nextPred) {
          setPrediction(nextPred);
        }
      }
      setLastUpdated(new Date());
    } catch (err) {
      if (isInitial) setError(err.response?.data?.detail || 'Failed to load token details.');
    } finally {
      if (isInitial) setLoading(false);
    }
  }, [appointmentId, playChime]);

  useEffect(() => {
    fetchTokenAndPrediction(true);
  }, [fetchTokenAndPrediction]);

  // Real-time queue subscription for instant status transitions and position changes
  const { connectionState } = useRealtimeQueue({
    userId: user?.id,
    appointmentId,
    onTokenUpdate: useCallback((updatedToken) => {
      if (!updatedToken) return;
      if (updatedToken.status === 'CALLED' && prevStatusRef.current !== 'CALLED') {
        playChime();
      }
      prevStatusRef.current = updatedToken.status;
      setLastUpdated(new Date());
      // Refresh token & AI wait time prediction immediately on any change
      fetchTokenAndPrediction(false);
    }, [fetchTokenAndPrediction, playChime]),
    onAppointmentUpdate: useCallback(() => {
      setLastUpdated(new Date());
      fetchTokenAndPrediction(false);
    }, [fetchTokenAndPrediction]),
  });

  const [openingPdf, setOpeningPdf] = useState(false);

  const getPdfBlobAndFilename = async () => {
    const res = await api.get(`/api/queue/token/${appointmentId}/pdf`, { responseType: 'blob' });
    let filename = `queue_token_${token?.token_number || appointmentId}.pdf`;
    const disposition = res.headers?.['content-disposition'] || res.headers?.['Content-Disposition'];
    if (disposition && disposition.includes('filename=')) {
      const match = disposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
      if (match && match[1]) {
        filename = match[1].replace(/['"]/g, '').trim();
      }
    }
    if (!filename.toLowerCase().endsWith('.pdf')) {
      filename += '.pdf';
    }
    const blob = res.data instanceof Blob ? res.data : new Blob([res.data], { type: 'application/pdf' });
    return { blob, filename };
  };

  const handleDownloadPDF = async () => {
    if (downloadingPdf) return;
    setDownloadingPdf(true);
    try {
      const { blob, filename } = await getPdfBlobAndFilename();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.style.display = 'none';
      link.href = url;
      link.download = filename;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      setTimeout(() => {
        if (document.body.contains(link)) {
          document.body.removeChild(link);
        }
        window.URL.revokeObjectURL(url);
      }, 1500);
    } catch (err) {
      console.error('Failed to download PDF', err);
      alert('Could not download PDF. Please try again.');
    } finally {
      setDownloadingPdf(false);
    }
  };

  const handleOpenPDF = async () => {
    if (openingPdf) return;
    setOpeningPdf(true);
    try {
      const { blob } = await getPdfBlobAndFilename();
      const url = window.URL.createObjectURL(blob);
      window.open(url, '_blank');
      setTimeout(() => window.URL.revokeObjectURL(url), 60000);
    } catch (err) {
      console.error('Failed to open PDF', err);
      alert('Could not open PDF. Please try again.');
    } finally {
      setOpeningPdf(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-2xl mx-auto py-16 text-center text-[var(--color-secondary)]">
        <div className="w-10 h-10 border-3 border-[var(--color-primary)] border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
        <p className="text-sm font-semibold">Generating your digital queue pass & AI predictions...</p>
      </div>
    );
  }

  if (error || !token) {
    return (
      <div className="max-w-2xl mx-auto py-8">
        <div className="p-6 rounded-[20px] bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900/60 text-red-700 dark:text-red-400">
          <p className="font-bold text-base mb-2">Error Loading Token</p>
          <p className="text-sm mb-4">{error || 'Token not found.'}</p>
          <Link
            to="/user/appointments"
            className="inline-flex px-4 py-2 bg-[var(--color-primary)] text-white text-xs font-bold rounded-xl"
          >
            ← View My Appointments
          </Link>
        </div>
      </div>
    );
  }

  const isCalled = token.status === 'CALLED';
  const isServing = token.status === 'SERVING';
  const isCompleted = token.status === 'COMPLETED';

  // Congestion indicator colors
  const getCongestionBadge = (level) => {
    switch (level) {
      case 'LOW':
        return 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300 border-emerald-300';
      case 'MODERATE':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-950/60 dark:text-blue-300 border-blue-300';
      case 'HIGH':
        return 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300 border-amber-300';
      case 'PEAK':
        return 'bg-red-100 text-red-800 dark:bg-red-950/60 dark:text-red-300 border-red-300';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300 border-gray-300';
    }
  };

  return (
    <div className="max-w-2xl mx-auto pb-14 space-y-6">
      {/* Turn Alert Banner when CALLED */}
      {isCalled && (
        <div className="p-5 rounded-[22px] bg-gradient-to-r from-amber-500/20 via-amber-400/15 to-amber-500/20 border-2 border-amber-400 dark:border-amber-500 shadow-lg animate-pulse flex items-center gap-4">
          <span className="text-4xl animate-bounce">🔔</span>
          <div className="flex-1">
            <h2 className="text-base sm:text-lg font-black text-amber-950 dark:text-amber-100 uppercase tracking-wide">
              It is Your Turn!
            </h2>
            <p className="text-xs sm:text-sm text-amber-900 dark:text-amber-200 mt-0.5 font-medium">
              Token <strong className="underline">{token.token_number}</strong> has been called. Please proceed immediately to your assigned service desk.
            </p>
          </div>
          <button
            type="button"
            onClick={playChime}
            className="p-2 rounded-xl bg-amber-400/30 hover:bg-amber-400/50 text-xs font-bold text-amber-950 dark:text-amber-100 transition-colors"
            title="Play alert chime"
          >
            🔊 Chime
          </button>
        </div>
      )}

      {/* Serving Banner */}
      {isServing && (
        <div className="p-5 rounded-[22px] bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-300 dark:border-emerald-800 shadow-sm flex items-center gap-3.5">
          <span className="text-2xl">⏱️</span>
          <div>
            <h2 className="text-sm font-bold text-emerald-900 dark:text-emerald-200">
              Session in Progress
            </h2>
            <p className="text-xs text-emerald-800 dark:text-emerald-300 mt-0.5">
              Token {token.token_number} is currently being served at the counter.
            </p>
          </div>
        </div>
      )}

      {/* Breadcrumb Header with Live Connection State & Last Updated */}
      <div>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[var(--color-primary)]">
            <span>✓ Verified Digital Pass</span>
          </div>

          <div className="flex items-center gap-2.5">
            {/* Live Connection State Badge */}
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

            {/* Last Updated Timestamp */}
            <span className="text-[11px] font-medium text-[var(--color-secondary)]">
              {lastUpdated
                ? `Updated ${lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}`
                : ''}
            </span>

            <button
              type="button"
              onClick={() => fetchTokenAndPrediction(false)}
              className="px-2.5 py-1 text-xs font-semibold text-[var(--color-secondary)] hover:text-[var(--color-text-main)] hover:bg-[var(--color-surface)] border border-[var(--color-border-subtle)] rounded-lg flex items-center gap-1 transition-all cursor-pointer"
              title="Re-sync queue state"
            >
              <span>🔄</span>
              <span>Sync</span>
            </button>
          </div>
        </div>

        <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-[var(--color-text-main)] mt-1">
          Queue Pass & Live Ticket
        </h1>
        <p className="text-xs sm:text-sm text-[var(--color-secondary)] mt-0.5">
          Present this pass at reception or keep this screen active to track your position in real time.
        </p>
      </div>

      {/* Real-Time Queue Monitor Bar */}
      <div className="p-4 sm:p-5 rounded-[22px] bg-[var(--color-surface)] border border-[var(--color-border-subtle)] shadow-xs grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-50 dark:bg-blue-950/70 border border-blue-200 dark:border-blue-800 text-blue-600 dark:text-blue-400 flex items-center justify-center text-lg shrink-0">
            ⚡
          </div>
          <div className="min-w-0">
            <p className="text-[10px] font-bold uppercase tracking-wider text-[var(--color-secondary)]">
              Currently Serving
            </p>
            <p className="text-sm font-extrabold text-[var(--color-text-main)] truncate mt-0.5">
              {token.currently_serving_token ? (
                <span className="text-[var(--color-primary)] font-mono font-black">
                  Token {token.currently_serving_token}
                </span>
              ) : (
                <span className="text-[var(--color-secondary)] italic">Awaiting staff call</span>
              )}
            </p>
            {token.currently_serving_counter && (
              <p className="text-[10px] text-[var(--color-secondary)] truncate">
                {token.currently_serving_counter}
              </p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3 border-t sm:border-t-0 sm:border-l border-[var(--color-border-subtle)] pt-3 sm:pt-0 sm:pl-4">
          <div className="w-10 h-10 rounded-xl bg-indigo-50 dark:bg-indigo-950/70 border border-indigo-200 dark:border-indigo-800 text-indigo-600 dark:text-indigo-400 flex items-center justify-center text-lg shrink-0">
            👥
          </div>
          <div className="min-w-0">
            <p className="text-[10px] font-bold uppercase tracking-wider text-[var(--color-secondary)]">
              People Ahead
            </p>
            <p className="text-sm font-extrabold text-[var(--color-text-main)] mt-0.5">
              {token.status === 'WAITING' ? (
                token.people_ahead === 0 ? (
                  <span className="text-emerald-600 dark:text-emerald-400 font-bold">You are next in line!</span>
                ) : (
                  <span>{token.people_ahead} eligible ahead</span>
                )
              ) : token.status === 'CALLED' ? (
                <span className="text-amber-500 font-bold animate-pulse">Proceed to desk</span>
              ) : token.status === 'SERVING' ? (
                <span className="text-emerald-600 dark:text-emerald-400 font-bold">Currently being served</span>
              ) : (
                <span className="text-[var(--color-secondary)]">0 ahead</span>
              )}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 border-t sm:border-t-0 sm:border-l border-[var(--color-border-subtle)] pt-3 sm:pt-0 sm:pl-4">
          <div className="w-10 h-10 rounded-xl bg-emerald-50 dark:bg-emerald-950/70 border border-emerald-200 dark:border-emerald-800 text-emerald-600 dark:text-emerald-400 flex items-center justify-center text-lg shrink-0">
            ⏱️
          </div>
          <div className="min-w-0">
            <p className="text-[10px] font-bold uppercase tracking-wider text-[var(--color-secondary)]">
              Estimated Wait
            </p>
            <p className="text-sm font-extrabold text-[var(--color-text-main)] mt-0.5">
              {token.status === 'WAITING' ? (
                token.estimated_waiting_time != null ? (
                  <span>~{token.estimated_waiting_time} mins</span>
                ) : (
                  <span className="text-xs text-[var(--color-secondary)] font-normal italic">
                    Estimated wait unavailable
                  </span>
                )
              ) : token.status === 'CALLED' ? (
                <span className="text-xs text-amber-500 font-bold">0 mins • Calling</span>
              ) : (
                <span className="text-xs text-[var(--color-secondary)]">0 mins</span>
              )}
            </p>
          </div>
        </div>
      </div>

      {/* Queue Progress Tracker */}
      <div className="p-4 sm:p-5 rounded-[22px] bg-[var(--color-surface)] border border-[var(--color-border-subtle)] shadow-xs">
        <div className="flex justify-between items-center text-xs font-bold text-[var(--color-secondary)] mb-3 px-1">
          <span>Queue Journey</span>
          <span className="text-[var(--color-primary)] font-extrabold">
            {isCompleted ? 'Completed' : isServing ? 'Being Served' : isCalled ? 'Now Calling' : `Position #${token.queue_position || 1}`}
          </span>
        </div>

        <div className="grid grid-cols-4 gap-2 text-center">
          <div className="space-y-1">
            <div className="h-2 rounded-full bg-[var(--color-primary)]"></div>
            <p className="text-[10px] font-bold text-[var(--color-primary)]">Issued</p>
          </div>
          <div className="space-y-1">
            <div className={`h-2 rounded-full ${token.status === 'WAITING' || isCalled || isServing || isCompleted ? 'bg-[var(--color-primary)]' : 'bg-gray-200 dark:bg-gray-700'}`}></div>
            <p className="text-[10px] font-bold text-[var(--color-text-main)]">In Line</p>
          </div>
          <div className="space-y-1">
            <div className={`h-2 rounded-full ${isCalled || isServing || isCompleted ? 'bg-amber-500' : 'bg-gray-200 dark:bg-gray-700'}`}></div>
            <p className={`text-[10px] font-bold ${isCalled ? 'text-amber-500 animate-pulse' : 'text-[var(--color-secondary)]'}`}>Called</p>
          </div>
          <div className="space-y-1">
            <div className={`h-2 rounded-full ${isCompleted ? 'bg-emerald-500' : 'bg-gray-200 dark:bg-gray-700'}`}></div>
            <p className={`text-[10px] font-bold ${isCompleted ? 'text-emerald-500' : 'text-[var(--color-secondary)]'}`}>Done</p>
          </div>
        </div>
      </div>

      {/* Main Ticket Card */}
      <div className={`bg-[var(--color-surface)] p-6 sm:p-8 rounded-[24px] border shadow-xs transition-all ${
        isCalled
          ? 'border-amber-400 dark:border-amber-600 ring-2 ring-amber-400/40'
          : 'border-[var(--color-border-subtle)]'
      }`}>
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-6 mb-8">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-widest text-[var(--color-secondary)] mb-2">
              Your Digital Token
            </p>
            <h2 className={`text-6xl sm:text-7xl font-extrabold tracking-tight ${isCalled ? 'text-amber-500 dark:text-amber-400' : 'text-[var(--color-primary)]'}`}>
              {token.token_number}
            </h2>
            <p className="font-bold text-base text-[var(--color-text-main)] mt-3">
              {token.branch_name}
            </p>
            <p className="text-xs text-[var(--color-secondary)] mt-0.5">
              {token.service_name} • {token.sector_name || 'Service'}
            </p>
          </div>

          <div className="text-left sm:text-right flex flex-col items-start sm:items-end">
            <span className={`inline-block text-xs font-bold px-3.5 py-1.5 rounded-full uppercase tracking-wider mb-3 ${
              isCalled
                ? 'bg-amber-400 text-amber-950 font-black animate-pulse'
                : 'bg-[var(--color-accent-subtle)] text-[var(--color-primary)]'
            }`}>
              {token.status}
            </span>

            <div className="bg-white p-3 rounded-2xl border border-[var(--color-border-subtle)] inline-block shadow-xs">
              <QRCodeSVG
                value={`${window.location.origin}/verify/token/${token.qr_secure_token}`}
                size={120}
                level="H"
                fgColor="#0F172A"
              />
            </div>
            <p className="text-[10px] text-[var(--color-secondary)] mt-2 font-medium">
              Official QR Check-in Pass
            </p>
          </div>
        </div>

        {/* Schedule metadata */}
        <div className="border-t border-[var(--color-border-subtle)] pt-5 space-y-2 text-xs">
          <div className="flex justify-between py-1">
            <span className="text-[var(--color-secondary)] font-medium">Scheduled Window:</span>
            <span className="font-bold text-[var(--color-text-main)]">
              {token.appointment_date} • {token.appointment_time}
            </span>
          </div>
          <div className="flex justify-between py-1">
            <span className="text-[var(--color-secondary)] font-medium">Arrival Policy:</span>
            <span className="font-bold text-[var(--color-text-main)]">
              Expected at reception 10 mins prior
            </span>
          </div>
        </div>

        {/* Step 9: Dynamic AI Prediction Card */}
        {prediction && (
          <div className="mt-6 rounded-2xl bg-gradient-to-br from-[var(--color-surface)] to-[var(--color-accent-subtle)]/30 border border-[var(--color-border-subtle)] p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 pb-3 border-b border-[var(--color-border-subtle)]">
              <div className="flex items-center gap-2">
                <span className="text-xl">🤖</span>
                <div>
                  <h3 className="text-xs font-extrabold text-[var(--color-text-main)] uppercase tracking-wider">
                    AI Dynamic Wait Prediction
                  </h3>
                  <p className="text-[11px] text-[var(--color-secondary)]">
                    Calculated from active desk throughput & real velocity
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-lg border uppercase tracking-wider ${getCongestionBadge(prediction.congestion_level)}`}>
                  {prediction.congestion_level} Traffic
                </span>
                <span className="text-[11px] font-bold text-[var(--color-primary)] bg-[var(--color-surface)] px-2.5 py-0.5 rounded-lg border border-[var(--color-border-subtle)]">
                  {prediction.confidence_score}% Accuracy
                </span>
              </div>
            </div>

            {/* Metrics grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
              <div className="p-3 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border-subtle)]">
                <p className="text-xl sm:text-2xl font-black text-[var(--color-primary)]">
                  {prediction.predicted_wait_minutes}m
                </p>
                <p className="text-[10px] text-[var(--color-secondary)] font-medium mt-0.5">
                  Est. Wait Time
                </p>
              </div>

              <div className="p-3 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border-subtle)]">
                <p className="text-xl sm:text-2xl font-black text-[var(--color-text-main)]">
                  {prediction.min_wait_minutes}–{prediction.max_wait_minutes}m
                </p>
                <p className="text-[10px] text-[var(--color-secondary)] font-medium mt-0.5">
                  Expected Range
                </p>
              </div>

              <div className="p-3 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border-subtle)]">
                <p className="text-xl sm:text-2xl font-black text-[var(--color-text-main)]">
                  {prediction.people_ahead}
                </p>
                <p className="text-[10px] text-[var(--color-secondary)] font-medium mt-0.5">
                  Ahead in Line
                </p>
              </div>

              <div className="p-3 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border-subtle)]">
                <p className="text-xl sm:text-2xl font-black text-[var(--color-text-main)]">
                  {prediction.active_counters_count}
                </p>
                <p className="text-[10px] text-[var(--color-secondary)] font-medium mt-0.5">
                  Active Desks
                </p>
              </div>
            </div>

            {/* AI Explanation Insight */}
            <p className="text-[11px] text-[var(--color-secondary)] italic leading-relaxed pt-1">
              💡 {prediction.ai_explanation}
            </p>
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <Link
          to="/user/appointments"
          className="bg-[var(--color-primary)] hover:opacity-90 text-white py-3 px-4 rounded-xl font-bold text-xs uppercase tracking-wider flex items-center justify-center transition-all shadow-xs text-center"
        >
          Appointments →
        </Link>
        <button
          type="button"
          onClick={handleOpenPDF}
          disabled={openingPdf}
          className="bg-[var(--color-surface)] hover:bg-[var(--color-surface-hover)] border border-[var(--color-border-subtle)] text-[var(--color-text-main)] py-3 px-4 rounded-xl font-bold text-xs uppercase tracking-wider flex items-center justify-center gap-1.5 transition-colors disabled:opacity-50 cursor-pointer"
        >
          <span>👁️</span>
          <span>{openingPdf ? 'Opening...' : 'Open PDF'}</span>
        </button>
        <button
          type="button"
          onClick={handleDownloadPDF}
          disabled={downloadingPdf}
          className="bg-[var(--color-surface)] hover:bg-[var(--color-surface-hover)] border border-[var(--color-border-subtle)] text-[var(--color-text-main)] py-3 px-4 rounded-xl font-bold text-xs uppercase tracking-wider flex items-center justify-center gap-1.5 transition-colors disabled:opacity-50 cursor-pointer"
        >
          <span>📥</span>
          <span>{downloadingPdf ? 'Downloading...' : 'Download PDF'}</span>
        </button>
      </div>
    </div>
  );
}
