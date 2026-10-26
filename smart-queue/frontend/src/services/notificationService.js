import api, { supabase } from './api';

export const notificationService = {
  /**
   * Fetch paginated user notifications.
   * Server validates user ownership and returns unread count.
   */
  async getNotifications({ unreadOnly = false, limit = 50, offset = 0 } = {}) {
    try {
      const res = await api.get('/api/notifications', {
        params: { unread_only: unreadOnly, limit, offset },
      });
      return res.data; // { notifications: [], total_count: int, unread_count: int }
    } catch (err) {
      if (!err.response) {
        try {
          const { data: { session } } = await supabase.auth.getSession();
          if (session?.user?.id) {
            let query = supabase
              .from('notifications')
              .select('*', { count: 'exact' })
              .eq('user_id', session.user.id)
              .order('created_at', { ascending: false })
              .range(offset, offset + limit - 1);

            if (unreadOnly) {
              query = query.eq('is_read', false);
            }

            const { data, count, error: sbErr } = await query;
            if (!sbErr && Array.isArray(data)) {
              return {
                notifications: data,
                total_count: count ?? data.length,
                unread_count: data.filter(n => !n.is_read).length,
              };
            }
          }
        } catch {
          // ignore
        }
        return { notifications: [], total_count: 0, unread_count: 0 };
      }
      throw err;
    }
  },

  /**
   * Mark a single notification as read.
   */
  async markAsRead(notificationId) {
    if (!notificationId) return null;
    const res = await api.patch(`/api/notifications/${notificationId}/read`);
    return res.data;
  },

  /**
   * Mark all notifications as read for current user.
   */
  async markAllAsRead() {
    const res = await api.post('/api/notifications/read-all');
    return res.data;
  },

  /**
   * Delete a notification permanently.
   */
  async deleteNotification(notificationId) {
    if (!notificationId) return null;
    const res = await api.delete(`/api/notifications/${notificationId}`);
    return res.data;
  },
};

export default notificationService;
