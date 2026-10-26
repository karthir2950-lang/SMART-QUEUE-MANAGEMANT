import api from './api';

export const queueService = {
  /**
   * Fetch current active queue token and live monitor state for authenticated user.
   */
  async getActiveToken() {
    const res = await api.get('/api/queue/active');
    return res.data;
  },

  /**
   * Fetch token and queue position details for an appointment.
   */
  async getToken(appointmentId) {
    if (!appointmentId) return null;
    const res = await api.get(`/api/queue/token/${appointmentId}`);
    return res.data;
  },

  /**
   * Fetch AI wait-time prediction and velocity bounds for an appointment token.
   */
  async getPrediction(appointmentId) {
    if (!appointmentId) return null;
    const res = await api.get(`/api/queue/token/${appointmentId}/prediction`);
    return res.data;
  },

  /**
   * Generate or retrieve queue token for an appointment.
   */
  async createToken(appointmentId) {
    if (!appointmentId) return null;
    const res = await api.post(`/api/queue/token/${appointmentId}`);
    return res.data;
  },

  /**
   * Verify secure QR token pass.
   */
  async verifyToken(secureToken) {
    if (!secureToken) return null;
    const res = await api.get(`/api/queue/verify/${secureToken}`);
    return res.data;
  },
};

export default queueService;
