import React, { useState, useEffect } from 'react';
import api from '../../services/api';

export default function AdminServices() {
  const [services, setServices] = useState([]);
  const [sectors, setSectors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Filters
  const [selectedSector, setSelectedSector] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  // Modal
  const [modalOpen, setModalOpen] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [currentId, setCurrentId] = useState(null);
  const [formData, setFormData] = useState({
    sector_id: '',
    name: '',
    description: '',
    average_service_time: 15,
    buffer_time: 5,
    status: 'ACTIVE'
  });
  const [submitting, setSubmitting] = useState(false);
  const [togglingStatusId, setTogglingStatusId] = useState(null);
  const [modalError, setModalError] = useState('');

  const loadData = async () => {
    try {
      setLoading(true);
      setError('');
      const [servicesRes, sectorsRes] = await Promise.all([
        api.get('/api/admin/services', {
          params: {
            sector_id: selectedSector || undefined,
            status: selectedStatus || undefined,
            search: searchTerm || undefined
          }
        }),
        api.get('/api/sectors')
      ]);
      setServices(servicesRes.data);
      setSectors(sectorsRes.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load services');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedSector, selectedStatus]);

  const handleOpenCreate = () => {
    setIsEditing(false);
    setCurrentId(null);
    setFormData({
      sector_id: sectors[0]?.id || '',
      name: '',
      description: '',
      average_service_time: 15,
      buffer_time: 5,
      status: 'ACTIVE'
    });
    setModalError('');
    setModalOpen(true);
  };

  const handleOpenEdit = (svc) => {
    setIsEditing(true);
    setCurrentId(svc.id);
    setFormData({
      sector_id: svc.sector_id,
      name: svc.name,
      description: svc.description || '',
      average_service_time: svc.average_service_time,
      buffer_time: svc.buffer_time || 0,
      status: svc.status
    });
    setModalError('');
    setModalOpen(true);
  };

  const handleStatusToggle = async (svc) => {
    if (togglingStatusId) return;
    setTogglingStatusId(svc.id);
    const nextStatus = svc.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE';
    try {
      await api.patch(`/api/admin/services/${svc.id}/status`, { status: nextStatus });
      await loadData();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to update service status');
    } finally {
      setTogglingStatusId(null);
    }
  };

  const handleSubmitModal = async (e) => {
    e.preventDefault();
    if (submitting) return;
    const avgTime = parseInt(formData.average_service_time, 10);
    const bufTime = parseInt(formData.buffer_time, 10) || 0;

    if (isNaN(avgTime) || avgTime < 0) {
      setModalError('Average service time cannot be negative');
      return;
    }
    if (isNaN(bufTime) || bufTime < 0) {
      setModalError('Buffer time cannot be negative');
      return;
    }

    setSubmitting(true);
    setModalError('');

    try {
      const payload = {
        ...formData,
        average_service_time: avgTime,
        buffer_time: bufTime
      };

      if (isEditing) {
        await api.put(`/api/admin/services/${currentId}`, payload);
      } else {
        await api.post('/api/admin/services', payload);
      }
      setModalOpen(false);
      await loadData();
    } catch (err) {
      setModalError(err.response?.data?.detail || 'Failed to save service');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto pb-12 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-bold uppercase tracking-widest text-[var(--color-primary)]">
            Service Catalog
          </span>
          <h1 className="text-3xl font-extrabold tracking-tight text-[var(--color-text-main)] mt-1">
            Services
          </h1>
          <p className="text-sm text-[var(--color-secondary)] mt-1">
            Manage available service offerings and estimated queue processing durations by sector.
          </p>
        </div>

        <button
          type="button"
          onClick={handleOpenCreate}
          className="self-start sm:self-auto px-5 py-2.5 bg-[var(--color-primary)] hover:opacity-90 text-white rounded-xl text-xs font-bold transition-all shadow-xs flex items-center gap-2"
        >
          <span>＋ Add Service</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-[var(--color-surface)] p-4 sm:p-5 rounded-[20px] border border-[var(--color-border-subtle)] flex flex-col md:flex-row gap-4 items-center justify-between">
        <div className="w-full md:w-80 flex items-center gap-2">
          <input
            type="text"
            placeholder="Search service name..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full px-3.5 py-2 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-input-bg)] text-xs text-[var(--color-text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
          />
          <button
            type="button"
            onClick={loadData}
            className="px-3 py-2 bg-[var(--color-accent-subtle)] text-[var(--color-primary)] rounded-xl text-xs font-bold"
          >
            Search
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          <select
            value={selectedSector}
            onChange={(e) => setSelectedSector(e.target.value)}
            className="px-3 py-2 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-input-bg)] text-xs text-[var(--color-text-main)]"
          >
            <option value="">All Sectors</option>
            {sectors.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>

          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="px-3 py-2 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-input-bg)] text-xs text-[var(--color-text-main)]"
          >
            <option value="">All Statuses</option>
            <option value="ACTIVE">ACTIVE</option>
            <option value="INACTIVE">INACTIVE</option>
          </select>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900/60 text-red-700 dark:text-red-400 text-sm font-medium">
          {error}
        </div>
      )}

      {/* Table */}
      <div className="bg-[var(--color-surface)] rounded-[22px] border border-[var(--color-border-subtle)] overflow-hidden shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[var(--color-canvas)] border-b border-[var(--color-border-subtle)] uppercase tracking-wider text-[var(--color-secondary)] font-bold">
              <tr>
                <th className="px-6 py-4">Service Name</th>
                <th className="px-6 py-4">Sector</th>
                <th className="px-6 py-4">Avg Duration</th>
                <th className="px-6 py-4">Buffer Time</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-border-subtle)]">
              {loading && (
                <tr>
                  <td colSpan="6" className="text-center py-12 text-[var(--color-secondary)]">
                    Loading services...
                  </td>
                </tr>
              )}

              {!loading && services.length === 0 && (
                <tr>
                  <td colSpan="6" className="text-center py-12 text-[var(--color-secondary)]">
                    No services found matching criteria.
                  </td>
                </tr>
              )}

              {!loading &&
                services.map((svc) => {
                  const sec = sectors.find((s) => s.id === svc.sector_id);
                  return (
                    <tr key={svc.id} className="hover:bg-[var(--color-surface-hover)] transition-colors">
                      <td className="px-6 py-4 font-bold text-[var(--color-text-main)] text-sm">
                        {svc.name}
                        {svc.description && (
                          <p className="text-[11px] font-normal text-[var(--color-secondary)] line-clamp-1 mt-0.5">
                            {svc.description}
                          </p>
                        )}
                      </td>
                      <td className="px-6 py-4 font-semibold text-[var(--color-primary)]">
                        {sec?.name || 'Sector'}
                      </td>
                      <td className="px-6 py-4 font-medium text-[var(--color-text-main)]">
                        ⏱️ {svc.average_service_time} min
                      </td>
                      <td className="px-6 py-4 text-[var(--color-secondary)]">
                        +{svc.buffer_time || 0} min buffer
                      </td>
                      <td className="px-6 py-4">
                        <span
                          className={`px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                            svc.status === 'ACTIVE'
                              ? 'bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-300'
                              : 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300'
                          }`}
                        >
                          {svc.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right space-x-2">
                        <button
                          type="button"
                          onClick={() => handleOpenEdit(svc)}
                          className="px-3 py-1.5 rounded-lg border border-[var(--color-border-subtle)] font-bold text-[11px] hover:bg-[var(--color-surface-hover)] text-[var(--color-text-main)] transition-colors"
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          disabled={togglingStatusId === svc.id}
                          onClick={() => handleStatusToggle(svc)}
                          className={`px-3 py-1.5 rounded-lg font-bold text-[11px] transition-colors disabled:opacity-50 ${
                            svc.status === 'ACTIVE'
                              ? 'bg-orange-50 text-orange-700 dark:bg-orange-950/40 dark:text-orange-300 hover:bg-orange-100'
                              : 'bg-teal-50 text-teal-700 dark:bg-teal-950/40 dark:text-teal-300 hover:bg-teal-100'
                          }`}
                        >
                          {togglingStatusId === svc.id ? 'Updating...' : svc.status === 'ACTIVE' ? 'Deactivate' : 'Activate'}
                        </button>
                      </td>
                    </tr>
                  );
                })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-[var(--color-surface)] w-full max-w-lg rounded-[24px] border border-[var(--color-border-subtle)] p-6 sm:p-8 shadow-2xl">
            <div className="flex items-center justify-between pb-4 border-b border-[var(--color-border-subtle)] mb-6">
              <h3 className="text-lg font-bold text-[var(--color-text-main)]">
                {isEditing ? 'Edit Service' : 'Create Service'}
              </h3>
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                className="p-1 rounded-lg border border-[var(--color-border-subtle)] text-xs"
              >
                ✕
              </button>
            </div>

            {modalError && (
              <div className="mb-4 p-3 rounded-xl bg-red-50 text-red-700 text-xs font-semibold">
                {modalError}
              </div>
            )}

            <form onSubmit={handleSubmitModal} className="space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase text-[var(--color-secondary)] mb-1">
                  Sector *
                </label>
                <select
                  required
                  value={formData.sector_id}
                  onChange={(e) => setFormData({ ...formData, sector_id: e.target.value })}
                  disabled={isEditing}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-input-bg)] text-xs text-[var(--color-text-main)]"
                >
                  {sectors.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-[var(--color-secondary)] mb-1">
                  Service Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Doctor Consultation"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-input-bg)] text-xs text-[var(--color-text-main)]"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-[var(--color-secondary)] mb-1">
                  Description
                </label>
                <textarea
                  rows="2"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-input-bg)] text-xs text-[var(--color-text-main)]"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold uppercase text-[var(--color-secondary)] mb-1">
                    Avg Service Time (mins) *
                  </label>
                  <input
                    type="number"
                    min="1"
                    required
                    value={formData.average_service_time}
                    onChange={(e) => setFormData({ ...formData, average_service_time: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-input-bg)] text-xs text-[var(--color-text-main)]"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase text-[var(--color-secondary)] mb-1">
                    Buffer Time (mins)
                  </label>
                  <input
                    type="number"
                    min="0"
                    value={formData.buffer_time}
                    onChange={(e) => setFormData({ ...formData, buffer_time: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-input-bg)] text-xs text-[var(--color-text-main)]"
                  />
                </div>
              </div>

              <div className="pt-4 flex items-center justify-end gap-3 border-t border-[var(--color-border-subtle)]">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="px-4 py-2 border border-[var(--color-border-subtle)] rounded-xl text-xs font-bold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-5 py-2 bg-[var(--color-primary)] text-white rounded-xl text-xs font-bold hover:opacity-90 disabled:opacity-50"
                >
                  {submitting ? 'Saving...' : 'Save Service'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
