import api from './api';

export const notificationService = {
  /**
   * Fetch paginated user notifications.
   * Server validates user ownership and returns unread count.
   */
  async getNotifications({ unreadOnly = false, limit = 50, offset = 0 } = {}) {
    const res = await api.get('/api/notifications', {
      params: { unread_only: unreadOnly, limit, offset },
    });
    return res.data; // { notifications: [], total_count: int, unread_count: int }
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
