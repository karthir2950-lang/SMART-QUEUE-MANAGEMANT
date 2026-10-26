import React, { useState, useEffect } from 'react';
import api from '../../services/api';

export default function AdminQueue() {
  const [tokens, setTokens] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  const fetchQueue = async () => {
    try {
      const res = await api.get('/api/admin/queue');
      setTokens(res.data);
    } catch (err) {
      setError('Failed to load queue.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
    // Poll every 10 seconds since realtime isn't requested yet
    const interval = setInterval(fetchQueue, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleAction = async (action, tokenId) => {
    setActionLoading(true);
    try {
      if (action === 'CALL_NEXT') {
        await api.post('/api/admin/queue/call-next');
      } else {
        await api.post(`/api/admin/queue/${tokenId}/${action}`);
      }
      await fetchQueue();
    } catch (err) {
      alert(err.response?.data?.detail || 'Action failed');
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-[var(--color-text-main)]">Queue Management</h1>
          <p className="text-[var(--color-secondary)]">Manage active tokens and service states.</p>
        </div>
        <button 
          onClick={() => handleAction('CALL_NEXT')}
          disabled={actionLoading}
          className="bg-[var(--color-primary)] hover:bg-[#066772] text-white px-6 py-3 rounded-[10px] font-semibold transition-colors disabled:opacity-50"
        >
          Call Next Token
        </button>
      </div>

      {error && <div className="text-[var(--color-destructive)] bg-[#FFF5F5] p-4 rounded-[10px] mb-6">{error}</div>}

      <div className="bg-white border border-[var(--color-border-subtle)] rounded-[18px] overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-[#F9FAFB] border-b border-[var(--color-border-subtle)] text-xs font-semibold text-[var(--color-secondary)] uppercase tracking-wider">
            <tr>
              <th className="px-6 py-4">Token</th>
              <th className="px-6 py-4">Status</th>
              <th className="px-6 py-4">Service</th>
              <th className="px-6 py-4">Wait Time</th>
              <th className="px-6 py-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--color-border-subtle)]">
            {loading && <tr><td colSpan="5" className="p-6 text-center text-gray-500">Loading...</td></tr>}
            {!loading && tokens.length === 0 && <tr><td colSpan="5" className="p-6 text-center text-gray-500">No active tokens in queue.</td></tr>}
            {!loading && tokens.map(t => (
              <tr key={t.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-6 py-4">
                  <span className="font-bold text-[var(--color-primary)] text-lg">{t.token_number}</span>
                </td>
                <td className="px-6 py-4">
                  <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase ${t.status === 'WAITING' ? 'bg-yellow-100 text-yellow-800' : t.status === 'CALLED' ? 'bg-blue-100 text-blue-800' : 'bg-green-100 text-green-800'}`}>
                    {t.status}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm text-[var(--color-text-main)]">
                  {t.service_name}
                </td>
                <td className="px-6 py-4 text-sm text-[var(--color-secondary)]">
                  {Math.round((new Date() - new Date(t.created_at)) / 60000)} mins
                </td>
                <td className="px-6 py-4 text-right space-x-2">
                  {t.status === 'WAITING' && (
                    <>
                      <button onClick={() => handleAction('skip', t.id)} disabled={actionLoading} className="text-xs font-semibold text-[var(--color-secondary)] hover:text-gray-900 border border-gray-300 px-3 py-1.5 rounded disabled:opacity-50">Skip</button>
                      <button onClick={() => handleAction('cancel', t.id)} disabled={actionLoading} className="text-xs font-semibold text-[var(--color-destructive)] hover:text-red-900 border border-red-200 px-3 py-1.5 rounded disabled:opacity-50">Cancel</button>
                    </>
                  )}
                  {t.status === 'CALLED' && (
                    <>
                      <button onClick={() => handleAction('start', t.id)} disabled={actionLoading} className="text-xs font-semibold bg-[var(--color-primary)] text-white hover:bg-[#066772] px-3 py-1.5 rounded disabled:opacity-50">Start Service</button>
                      <button onClick={() => handleAction('no-show', t.id)} disabled={actionLoading} className="text-xs font-semibold text-[var(--color-secondary)] hover:text-gray-900 border border-gray-300 px-3 py-1.5 rounded disabled:opacity-50">No Show</button>
                    </>
                  )}
                  {t.status === 'SERVING' && (
                    <button onClick={() => handleAction('complete', t.id)} disabled={actionLoading} className="text-xs font-semibold bg-green-600 text-white hover:bg-green-700 px-3 py-1.5 rounded disabled:opacity-50">Complete Service</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
