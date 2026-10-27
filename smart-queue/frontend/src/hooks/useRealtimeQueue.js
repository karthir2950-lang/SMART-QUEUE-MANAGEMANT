import { useEffect, useRef, useState, useCallback } from 'react';
import { supabase } from '../services/api';

/**
 * useRealtimeQueue
 * 
 * Reusable React hook for real-time queue tokens, appointments, and notification updates.
 * Implements Supabase Realtime channel subscription with automatic SSE fallback,
 * idempotent event handling, memory leak protection, and clean subscription lifecycle.
 *
 * @param {Object} options
 * @param {string} [options.userId] - Current authenticated user ID (required for user subscriptions)
 * @param {string} [options.appointmentId] - Specific appointment ID to watch
 * @param {string} [options.branchId] - Specific branch ID to watch (for staff dashboards)
 * @param {Function} [options.onTokenUpdate] - Callback when queue token status/position changes
 * @param {Function} [options.onAppointmentUpdate] - Callback when appointment record changes
 * @param {Function} [options.onNotification] - Callback when a new notification is generated
 * @param {Function} [options.onQueueRefresh] - Generic callback to trigger re-fetch
 */
export function useRealtimeQueue({
  userId,
  appointmentId,
  branchId,
  onTokenUpdate,
  onAppointmentUpdate,
  onNotification,
  onQueueRefresh,
} = {}) {
  const [isConnected, setIsConnected] = useState(false);
  const [connectionState, setConnectionState] = useState('Reconnecting');
  const [lastEvent, setLastEvent] = useState(null);

  // Store latest callbacks in refs to avoid re-subscribing on every parent render
  const callbacksRef = useRef({
    onTokenUpdate,
    onAppointmentUpdate,
    onNotification,
    onQueueRefresh,
  });

  useEffect(() => {
    callbacksRef.current = {
      onTokenUpdate,
      onAppointmentUpdate,
      onNotification,
      onQueueRefresh,
    };
  }, [onTokenUpdate, onAppointmentUpdate, onNotification, onQueueRefresh]);

  // Idempotency tracking to prevent duplicate actions from dual channels or rapid reconnects
  const processedEventsRef = useRef(new Map());

  const isDuplicate = useCallback((key, ttlMs = 2500) => {
    const now = Date.now();
    const prevTime = processedEventsRef.current.get(key);
    if (prevTime && (now - prevTime) < ttlMs) {
      return true;
    }
    processedEventsRef.current.set(key, now);

    // Prune stale keys
    if (processedEventsRef.current.size > 200) {
      for (const [k, time] of processedEventsRef.current.entries()) {
        if (now - time > ttlMs) {
          processedEventsRef.current.delete(k);
        }
      }
    }
    return false;
  }, []);

  useEffect(() => {
    // Start subscriptions only when authenticated user or required identifiers are present
    if (!userId && !branchId && !appointmentId) {
      setIsConnected(false);
      return;
    }

    let isSubscribed = true;
    let channel = null;

    try {
      const channelId = `sq_rt_${userId || 'anon'}_${branchId || 'nobranch'}_${appointmentId || 'noappt'}_${Math.random().toString(36).substring(2, 9)}_${Date.now()}`;
      channel = supabase.channel(channelId);

      // 1. Supabase Realtime: Notifications Table
      if (userId) {
        channel.on(
          'postgres_changes',
          {
            event: '*',
            schema: 'public',
            table: 'notifications',
            filter: `user_id=eq.${userId}`,
          },
          (payload) => {
            if (!isSubscribed) return;
            const notif = payload.new;
            if (!notif || !notif.id) return;
            const dedupKey = `sb_notif_${notif.id}_${notif.is_read}`;
            if (isDuplicate(dedupKey)) return;

            setLastEvent({ type: 'NOTIFICATION', data: notif, timestamp: Date.now() });
            callbacksRef.current.onNotification?.(notif);
          }
        );

        // 2. Supabase Realtime: Appointments Table
        channel.on(
          'postgres_changes',
          {
            event: '*',
            schema: 'public',
            table: 'appointments',
            filter: `user_id=eq.${userId}`,
          },
          (payload) => {
            if (!isSubscribed) return;
            const appt = payload.new;
            if (!appt || !appt.id) return;
            const dedupKey = `sb_appt_${appt.id}_${appt.status}`;
            if (isDuplicate(dedupKey)) return;

            setLastEvent({ type: 'APPOINTMENT', data: appt, timestamp: Date.now() });
            callbacksRef.current.onAppointmentUpdate?.(appt);
            callbacksRef.current.onQueueRefresh?.(appt);
          }
        );
      }

      // 3. Supabase Realtime: Queue Tokens Table
      channel.on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: 'queue_tokens',
        },
        (payload) => {
          if (!isSubscribed) return;
          const token = payload.new;
          if (!token || !token.id) return;

          // If specific appointmentId is being watched, only dispatch if matching
          if (appointmentId && token.appointment_id && token.appointment_id !== appointmentId) {
            return;
          }

          const dedupKey = `sb_token_${token.id}_${token.status}_${token.queue_position}`;
          if (isDuplicate(dedupKey)) return;

          setLastEvent({ type: 'TOKEN', data: token, timestamp: Date.now() });
          callbacksRef.current.onTokenUpdate?.(token);
          callbacksRef.current.onQueueRefresh?.(token);
        }
      );

      channel.subscribe((status) => {
        if (!isSubscribed) return;
        if (status === 'SUBSCRIBED') {
          setIsConnected(true);
          setConnectionState('Live');
        } else if (status === 'TIMED_OUT') {
          setConnectionState('Reconnecting');
        } else if (status === 'CLOSED' || status === 'CHANNEL_ERROR') {
          setIsConnected(false);
          setConnectionState('Offline');
        }
      });
    } catch (realtimeErr) {
      console.warn('Realtime channel subscription notice:', realtimeErr?.message || realtimeErr);
    }

    // 4. Dual-Channel: Live Server-Sent Events stream as resilient secondary pipeline
    let eventSource = null;
    const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
    const streamEndpoint = userId
      ? `${apiBase}/api/stream/user/${userId}`
      : branchId
        ? `${apiBase}/api/stream/branch/${branchId}`
        : null;

    if (streamEndpoint && typeof window !== 'undefined' && window.EventSource) {
      try {
        eventSource = new EventSource(streamEndpoint);

        eventSource.onopen = () => {
          if (isSubscribed) {
            setIsConnected(true);
            setConnectionState('Live');
          }
        };

        eventSource.onmessage = (event) => {
          if (!isSubscribed || !event.data) return;
          try {
            const parsed = JSON.parse(event.data);
            if (!parsed || parsed.event === 'CONNECTED') return;

            const dedupKey = `sse_${parsed.event}_${parsed.data?.id || parsed.token_id || parsed.appointment_id || Date.now()}`;
            if (isDuplicate(dedupKey)) return;

            setLastEvent({ type: parsed.event, data: parsed, timestamp: Date.now() });

            if (parsed.event === 'NOTIFICATION') {
              callbacksRef.current.onNotification?.(parsed.data);
            } else if (parsed.event === 'QUEUE_UPDATED') {
              callbacksRef.current.onTokenUpdate?.(parsed);
              callbacksRef.current.onQueueRefresh?.(parsed);
            } else if (parsed.event === 'APPOINTMENT_UPDATED') {
              callbacksRef.current.onAppointmentUpdate?.(parsed);
              callbacksRef.current.onQueueRefresh?.(parsed);
            }
          } catch {
            // Ignore heartbeat comments
          }
        };

        eventSource.onerror = () => {
          // EventSource automatically retries connection in the background
          if (isSubscribed) {
            setConnectionState((prev) => (prev === 'Live' ? 'Reconnecting' : prev));
          }
        };
      } catch (e) {
        console.warn('SSE stream notice:', e?.message || e);
      }
    }

    // 5. Clean subscription lifecycle on unmount, logout, or identifier change
    return () => {
      isSubscribed = false;
      try {
        supabase.removeChannel(channel);
      } catch {
        // channel cleanup
      }
      if (eventSource) {
        eventSource.close();
      }
      setIsConnected(false);
      setConnectionState('Offline');
    };
  }, [userId, appointmentId, branchId, isDuplicate]);

  return {
    isConnected,
    connectionState,
    lastEvent,
  };
}

export default useRealtimeQueue;
