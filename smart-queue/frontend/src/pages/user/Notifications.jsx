import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import notificationService from '../../services/notificationService';
import { useAuth } from '../../context/AuthContext';
import { useRealtimeQueue } from '../../hooks/useRealtimeQueue';

export default function Notifications() {
  const { user } = useAuth();
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [filter, setFilter] = useState('ALL'); // 'ALL' | 'UNREAD'
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  const fetchNotifications = useCallback(async () => {
    try {
      setError('');
      const data = await notificationService.getNotifications({
        unreadOnly: filter === 'UNREAD',
      });
      setNotifications(data.notifications || []);
      setUnreadCount(data.unread_count || 0);
    } catch (err) {
      console.error('Failed to load notifications:', err);
      const errorMsg = !err.response
        ? 'Unable to connect to the backend server. Please verify the service is running.'
        : (err.response?.data?.detail || 'Failed to load notifications. Please try again.');
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  // Real-time notification lifecycle subscription
  useRealtimeQueue({
    userId: user?.id,
    onNotification: useCallback((newNotif) => {
      if (!newNotif || !newNotif.id) return;
      setNotifications((prev) => {
        const index = prev.findIndex((n) => n.id === newNotif.id);
        if (index >= 0) {
          const updated = [...prev];
          updated[index] = { ...updated[index], ...newNotif };
          return updated;
        }
        if (filter === 'UNREAD' && newNotif.is_read) {
          return prev;
        }
        return [newNotif, ...prev];
      });
      if (!newNotif.is_read) {
        setUnreadCount((c) => c + 1);
      }
    }, [filter]),
  });

  const handleMarkAsRead = async (id, e) => {
    e?.stopPropagation();
    try {
      await notificationService.markAsRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch (err) {
      console.error('Failed to mark read:', err);
    }
  };

  const handleMarkAllRead = async () => {
    if (actionLoading || unreadCount === 0) return;
    setActionLoading(true);
    try {
      await notificationService.markAllAsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch (err) {
      console.error('Failed to mark all read:', err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleDelete = async (id, e) => {
    e?.stopPropagation();
    try {
      await notificationService.deleteNotification(id);
      setNotifications((prev) => prev.filter((n) => n.id !== id));
      fetchNotifications();
    } catch (err) {
      console.error('Failed to delete notification:', err);
    }
  };

  const getTypeBadge = (type) => {
    switch (type) {
      case 'CALLED':
        return {
          icon: '🔔',
          label: 'Called to Desk',
          className: 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300 border-amber-300 dark:border-amber-800'
        };
      case 'TURN_ALERT':
        return {
          icon: '⚠️',
          label: 'Approaching Turn',
          className: 'bg-orange-100 text-orange-800 dark:bg-orange-950/60 dark:text-orange-300 border-orange-300 dark:border-orange-800'
        };
      case 'TOKEN_CREATED':
        return {
          icon: '🎟️',
          label: 'Token Generated',
          className: 'bg-blue-100 text-blue-800 dark:bg-blue-950/60 dark:text-blue-300 border-blue-300 dark:border-blue-800'
        };
      case 'APPOINTMENT_BOOKED':
        return {
          icon: '📅',
          label: 'Appointment Booked',
          className: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300 border-emerald-300 dark:border-emerald-800'
        };
      case 'APPOINTMENT_CANCELLED':
        return {
          icon: '🚫',
          label: 'Appointment Cancelled',
          className: 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300 border-rose-300 dark:border-rose-800'
        };
      case 'SERVING':
        return {
          icon: '⏱️',
          label: 'Service Active',
          className: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300 border-emerald-300 dark:border-emerald-800'
        };
      case 'COMPLETED':
        return {
          icon: '✓',
          label: 'Completed',
          className: 'bg-slate-100 text-slate-800 dark:bg-slate-800/60 dark:text-slate-300 border-slate-300 dark:border-slate-700'
        };
      case 'SKIPPED':
        return {
          icon: '⏭️',
          label: 'Skipped',
          className: 'bg-purple-100 text-purple-800 dark:bg-purple-950/60 dark:text-purple-300 border-purple-300 dark:border-purple-800'
        };
      case 'NO_SHOW':
        return {
          icon: '✕',
          label: 'No-Show',
          className: 'bg-red-100 text-red-800 dark:bg-red-950/60 dark:text-red-300 border-red-300 dark:border-red-800'
        };
      default:
        return {
          icon: 'ℹ️',
          label: 'System Notice',
          className: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300 border-gray-300 dark:border-gray-700'
        };
    }
  };

  const formatTimestamp = (dateStr) => {
    if (!dateStr) return '';
    try {
      const d = new Date(dateStr);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ' • ' + d.toLocaleDateString();
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-[var(--color-text-main)]">
              Notifications
            </h1>
            {unreadCount > 0 && (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-[var(--color-primary)] text-white animate-pulse">
                {unreadCount} new
              </span>
            )}
          </div>
          <p className="text-xs sm:text-sm text-[var(--color-secondary)] mt-1">
            Real-time queue announcements, turn alerts, and visit milestones.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {unreadCount > 0 && (
            <button
              type="button"
              onClick={handleMarkAllRead}
              disabled={actionLoading}
              className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-[var(--color-surface)] border border-[var(--color-border-subtle)] text-[var(--color-text-main)] hover:bg-[var(--color-surface-hover)] shadow-xs transition-colors cursor-pointer"
            >
              Mark all as read
            </button>
          )}
          <button
            type="button"
            onClick={fetchNotifications}
            className="p-2 rounded-xl text-xs font-semibold bg-[var(--color-surface)] border border-[var(--color-border-subtle)] text-[var(--color-text-main)] hover:bg-[var(--color-surface-hover)] shadow-xs"
            title="Refresh"
          >
            🔄
          </button>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 p-1.5 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border-subtle)] w-fit shadow-xs">
        <button
          type="button"
          onClick={() => setFilter('ALL')}
          className={`px-4 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
            filter === 'ALL'
              ? 'bg-[var(--color-primary)] text-white shadow-xs'
              : 'text-[var(--color-secondary)] hover:text-[var(--color-text-main)]'
          }`}
        >
          All
        </button>
        <button
          type="button"
          onClick={() => setFilter('UNREAD')}
          className={`px-4 py-1.5 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer ${
            filter === 'UNREAD'
              ? 'bg-[var(--color-primary)] text-white shadow-xs'
              : 'text-[var(--color-secondary)] hover:text-[var(--color-text-main)]'
          }`}
        >
          <span>Unread</span>
          {unreadCount > 0 && (
            <span className={`px-1.5 py-0.2 rounded-full text-[10px] font-bold ${
              filter === 'UNREAD' ? 'bg-white text-[var(--color-primary)]' : 'bg-[var(--color-primary)] text-white'
            }`}>
              {unreadCount}
            </span>
          )}
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900/60 text-red-700 dark:text-red-400 text-sm font-medium flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="text-base">⚠️</span>
            <span>{error}</span>
          </div>
          <button
            type="button"
            onClick={fetchNotifications}
            className="self-start sm:self-auto px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-xl text-xs font-semibold transition-all shadow-xs active:scale-95 cursor-pointer flex items-center gap-1.5"
          >
            <span>↻</span>
            <span>Retry</span>
          </button>
        </div>
      )}

      {/* Notifications List */}
      {loading ? (
        <div className="py-12 text-center text-[var(--color-secondary)]">
          <div className="w-8 h-8 border-3 border-[var(--color-primary)] border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
          <p className="text-xs font-medium">Loading notifications...</p>
        </div>
      ) : notifications.length === 0 ? (
        <div className="bg-[var(--color-surface)] rounded-[20px] border border-[var(--color-border-subtle)] p-12 text-center shadow-xs">
          <span className="text-4xl mb-3 block">🔔</span>
          <p className="font-bold text-base text-[var(--color-text-main)] mb-1">
            {filter === 'UNREAD' ? 'No unread notifications' : "You're all caught up!"}
          </p>
          <p className="text-xs text-[var(--color-secondary)] max-w-sm mx-auto">
            Live updates will appear here whenever your queue ticket is called or approaching.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {notifications.map((item) => {
            const badge = getTypeBadge(item.type);
            const isCallOut = item.type === 'CALLED';

            return (
              <div
                key={item.id}
                className={`p-4 sm:p-5 rounded-[20px] border transition-all relative overflow-hidden ${
                  !item.is_read
                    ? isCallOut
                      ? 'bg-amber-50/90 dark:bg-amber-950/40 border-amber-300 dark:border-amber-800 shadow-sm ring-1 ring-amber-400/40'
                      : 'bg-[var(--color-surface)] border-[var(--color-primary)]/40 shadow-xs ring-1 ring-[var(--color-primary)]/20'
                    : 'bg-[var(--color-surface)] border-[var(--color-border-subtle)] opacity-85 hover:opacity-100'
                }`}
              >
                {!item.is_read && (
                  <span className="absolute top-4 right-4 w-2.5 h-2.5 rounded-full bg-[var(--color-primary)]"></span>
                )}

                <div className="flex items-start gap-3.5">
                  <div className="w-10 h-10 rounded-xl flex items-center justify-center text-lg flex-shrink-0 bg-[var(--color-accent-subtle)]">
                    {badge.icon}
                  </div>

                  <div className="flex-1 min-w-0 pr-6">
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-lg border uppercase tracking-wider ${badge.className}`}>
                        {badge.label}
                      </span>
                      <span className="text-[11px] text-[var(--color-secondary)]">
                        {formatTimestamp(item.created_at)}
                      </span>
                    </div>

                    <h2 className={`text-sm sm:text-base font-bold ${isCallOut ? 'text-amber-900 dark:text-amber-200' : 'text-[var(--color-text-main)]'}`}>
                      {item.title}
                    </h2>

                    <p className={`text-xs mt-1 leading-relaxed ${isCallOut ? 'text-amber-800 dark:text-amber-300 font-medium' : 'text-[var(--color-secondary)]'}`}>
                      {item.message}
                    </p>

                    <div className="mt-3 flex flex-wrap items-center gap-2.5 pt-2 border-t border-[var(--color-border-subtle)]/60">
                      {item.appointment_id && (
                        <Link
                          to={`/user/token/${item.appointment_id}`}
                          className="text-xs font-bold text-[var(--color-primary)] hover:underline inline-flex items-center gap-1"
                        >
                          <span>View Live Token</span>
                          <span>→</span>
                        </Link>
                      )}

                      {!item.is_read && (
                        <button
                          type="button"
                          onClick={(e) => handleMarkAsRead(item.id, e)}
                          className="text-xs font-medium text-[var(--color-secondary)] hover:text-[var(--color-text-main)] cursor-pointer"
                        >
                          Mark as read
                        </button>
                      )}

                      <button
                        type="button"
                        onClick={(e) => handleDelete(item.id, e)}
                        className="text-xs font-medium text-red-500 hover:text-red-700 ml-auto cursor-pointer"
                        title="Delete notification"
                      >
                        🗑️ Delete
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
