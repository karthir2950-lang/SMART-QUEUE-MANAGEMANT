import React, { useState, useEffect } from 'react';
import api from '../../services/api';

export default function AdminOrganizations() {
  const [organizations, setOrganizations] = useState([]);
  const [sectors, setSectors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Filters
  const [selectedSector, setSelectedSector] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  // Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [viewModalOpen, setViewModalOpen] = useState(false);
  const [viewingOrg, setViewingOrg] = useState(null);
  const [togglingStatusId, setTogglingStatusId] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [currentId, setCurrentId] = useState(null);
  const [formData, setFormData] = useState({
    sector_id: '',
    name: '',
    description: '',
    phone: '',
    email: '',
    address: '',
    city: '',
    state: '',
    pincode: '',
    status: 'ACTIVE'
  });
  const [submitting, setSubmitting] = useState(false);
  const [modalError, setModalError] = useState('');

  const loadData = async () => {
    try {
      setLoading(true);
      setError('');
      const [orgsRes, sectorsRes] = await Promise.all([
        api.get('/api/admin/organizations', {
          params: {
            sector_id: selectedSector || undefined,
            status: selectedStatus || undefined,
            search: searchTerm || undefined
          }
        }),
        api.get('/api/sectors')
      ]);
      setOrganizations(orgsRes.data);
      setSectors(sectorsRes.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load organizations');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedSector, selectedStatus]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    loadData();
  };

  const handleOpenCreate = () => {
    setIsEditing(false);
    setCurrentId(null);
    setFormData({
      sector_id: sectors[0]?.id || '',
      name: '',
      description: '',
      phone: '',
      email: '',
      address: '',
      city: '',
      state: '',
      pincode: '',
      status: 'ACTIVE'
    });
    setModalError('');
    setModalOpen(true);
  };

  const handleOpenEdit = (org) => {
    setIsEditing(true);
    setCurrentId(org.id);
    setFormData({
      sector_id: org.sector_id,
      name: org.name,
      description: org.description || '',
      phone: org.phone || '',
      email: org.email || '',
      address: org.address || '',
      city: org.city || '',
      state: org.state || '',
      pincode: org.pincode || '',
      status: org.status
    });
    setModalError('');
    setModalOpen(true);
  };

  const handleOpenView = (org) => {
    setViewingOrg(org);
    setViewModalOpen(true);
  };

  const handleStatusToggle = async (org) => {
    if (togglingStatusId) return;
    setTogglingStatusId(org.id);
    const nextStatus = org.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE';
    try {
      await api.patch(`/api/admin/organizations/${org.id}/status`, { status: nextStatus });
      await loadData();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to update organization status');
    } finally {
      setTogglingStatusId(null);
    }
  };

  const handleSubmitModal = async (e) => {
    e.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    setModalError('');

    try {
      if (isEditing) {
        await api.put(`/api/admin/organizations/${currentId}`, formData);
      } else {
        await api.post('/api/admin/organizations', formData);
      }
      setModalOpen(false);
      loadData();
    } catch (err) {
      setModalError(err.response?.data?.detail || 'Failed to save organization');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto pb-12 space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-bold uppercase tracking-widest text-[var(--color-primary)]">
            Administration
          </span>
          <h1 className="text-3xl font-extrabold tracking-tight text-[var(--color-text-main)] mt-1">
            Organizations
          </h1>
          <p className="text-sm text-[var(--color-secondary)] mt-1">
            Manage provider organizations across sectors. Status controls protect historical records.
          </p>
        </div>

        <button
          type="button"
          onClick={handleOpenCreate}
          className="self-start sm:self-auto px-5 py-2.5 bg-[var(--color-primary)] hover:opacity-90 text-white rounded-xl text-xs font-bold transition-all shadow-xs flex items-center gap-2"
        >
          <span>＋ Add Organization</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-[var(--color-surface)] p-4 sm:p-5 rounded-[20px] border border-[var(--color-border-subtle)] flex flex-col md:flex-row gap-4 items-center justify-between">
        <form onSubmit={handleSearchSubmit} className="w-full md:w-80 flex items-center gap-2">
          <input
            type="text"
            placeholder="Search by name or city..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full px-3.5 py-2 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-input-bg)] text-xs text-[var(--color-text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
          />
          <button
            type="submit"
            className="px-3 py-2 bg-[var(--color-accent-subtle)] text-[var(--color-primary)] rounded-xl text-xs font-bold"
          >
            Search
          </button>
        </form>

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
                <th className="px-6 py-4">Organization Name</th>
                <th className="px-6 py-4">Sector</th>
                <th className="px-6 py-4">Location</th>
                <th className="px-6 py-4">Contact</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-border-subtle)]">
              {loading && (
                <tr>
                  <td colSpan="6" className="text-center py-12 text-[var(--color-secondary)]">
                    Loading organizations...
                  </td>
                </tr>
              )}

              {!loading && organizations.length === 0 && (
                <tr>
                  <td colSpan="6" className="text-center py-12 text-[var(--color-secondary)]">
                    No organizations found matching criteria.
                  </td>
                </tr>
              )}

              {!loading &&
                organizations.map((org) => {
                  const sec = sectors.find((s) => s.id === org.sector_id);
                  return (
                    <tr key={org.id} className="hover:bg-[var(--color-surface-hover)] transition-colors">
                      <td className="px-6 py-4 font-bold text-[var(--color-text-main)] text-sm">
                        {org.name}
                        {org.description && (
                          <p className="text-[11px] font-normal text-[var(--color-secondary)] line-clamp-1 mt-0.5">
                            {org.description}
                          </p>
                        )}
                      </td>
                      <td className="px-6 py-4 font-semibold text-[var(--color-primary)]">
                        {sec?.name || 'Sector'}
                      </td>
                      <td className="px-6 py-4 text-[var(--color-secondary)]">
                        {org.city ? `${org.city}${org.state ? `, ${org.state}` : ''}` : 'Not specified'}
                      </td>
                      <td className="px-6 py-4 text-[var(--color-secondary)]">
                        {org.email || org.phone || '—'}
                      </td>
                      <td className="px-6 py-4">
                        <span
                          className={`px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                            org.status === 'ACTIVE'
                              ? 'bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-300'
                              : 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300'
                          }`}
                        >
                          {org.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right space-x-2">
                        <button
                          type="button"
                          onClick={() => handleOpenView(org)}
                          className="px-3 py-1.5 rounded-lg border border-[var(--color-border-subtle)] font-bold text-[11px] hover:bg-[var(--color-surface-hover)] text-[var(--color-text-main)] transition-colors"
                        >
                          View
                        </button>
                        <button
                          type="button"
                          onClick={() => handleOpenEdit(org)}
                          className="px-3 py-1.5 rounded-lg border border-[var(--color-border-subtle)] font-bold text-[11px] hover:bg-[var(--color-surface-hover)] text-[var(--color-text-main)] transition-colors"
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          disabled={togglingStatusId === org.id}
                          onClick={() => handleStatusToggle(org)}
                          className={`px-3 py-1.5 rounded-lg font-bold text-[11px] transition-colors disabled:opacity-50 ${
                            org.status === 'ACTIVE'
                              ? 'bg-orange-50 text-orange-700 dark:bg-orange-950/40 dark:text-orange-300 hover:bg-orange-100'
                              : 'bg-teal-50 text-teal-700 dark:bg-teal-950/40 dark:text-teal-300 hover:bg-teal-100'
                          }`}
                        >
                          {togglingStatusId === org.id ? 'Updating...' : org.status === 'ACTIVE' ? 'Deactivate' : 'Activate'}
                        </button>
                      </td>
                    </tr>
                  );
                })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create / Edit Modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-[var(--color-surface)] w-full max-w-lg rounded-[24px] border border-[var(--color-border-subtle)] p-6 sm:p-8 shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-4 border-b border-[var(--color-border-subtle)] mb-6">
              <h3 className="text-lg font-bold text-[var(--color-text-main)]">
                {isEditing ? 'Edit Organization' : 'Create Organization'}
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
                  Organization Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. City General Hospital"
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
                    City
                  </label>
                  <input
                    type="text"
                    value={formData.city}
                    onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-input-bg)] text-xs text-[var(--color-text-main)]"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase text-[var(--color-secondary)] mb-1">
                    State
                  </label>
                  <input
                    type="text"
                    value={formData.state}
                    onChange={(e) => setFormData({ ...formData, state: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-input-bg)] text-xs text-[var(--color-text-main)]"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold uppercase text-[var(--color-secondary)] mb-1">
                    Email
                  </label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-input-bg)] text-xs text-[var(--color-text-main)]"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase text-[var(--color-secondary)] mb-1">
                    Phone
                  </label>
                  <input
                    type="text"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
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
                  {submitting ? 'Saving...' : 'Save Organization'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      {/* View Details Modal */}
      {viewModalOpen && viewingOrg && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-[var(--color-surface)] w-full max-w-lg rounded-[24px] border border-[var(--color-border-subtle)] p-6 sm:p-8 shadow-2xl">
            <div className="flex items-center justify-between pb-4 border-b border-[var(--color-border-subtle)] mb-6">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--color-primary)]">Organization Details</span>
                <h3 className="text-xl font-bold text-[var(--color-text-main)] mt-0.5">{viewingOrg.name}</h3>
              </div>
              <button
                type="button"
                onClick={() => setViewModalOpen(false)}
                className="p-1 rounded-lg border border-[var(--color-border-subtle)] text-xs"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-[var(--color-canvas)] p-3 rounded-xl border border-[var(--color-border-subtle)]">
                  <p className="text-[10px] uppercase font-bold text-[var(--color-secondary)]">Sector</p>
                  <p className="font-semibold text-sm text-[var(--color-primary)] mt-0.5">
                    {sectors.find((s) => s.id === viewingOrg.sector_id)?.name || 'General'}
                  </p>
                </div>
                <div className="bg-[var(--color-canvas)] p-3 rounded-xl border border-[var(--color-border-subtle)]">
                  <p className="text-[10px] uppercase font-bold text-[var(--color-secondary)]">Status</p>
                  <span
                    className={`inline-block px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider mt-1 ${
                      viewingOrg.status === 'ACTIVE'
                        ? 'bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-300'
                        : 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300'
                    }`}
                  >
                    {viewingOrg.status}
                  </span>
                </div>
              </div>

              {viewingOrg.description && (
                <div>
                  <p className="text-[10px] uppercase font-bold text-[var(--color-secondary)] mb-1">Description</p>
                  <p className="p-3 rounded-xl bg-[var(--color-canvas)] border border-[var(--color-border-subtle)] text-[var(--color-text-main)] leading-relaxed">
                    {viewingOrg.description}
                  </p>
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <p className="text-[10px] uppercase font-bold text-[var(--color-secondary)] mb-1">Location</p>
                  <p className="text-[var(--color-text-main)] font-medium">
                    {viewingOrg.city ? `${viewingOrg.city}${viewingOrg.state ? `, ${viewingOrg.state}` : ''}` : 'Not specified'}
                  </p>
                  {viewingOrg.pincode && <p className="text-[var(--color-secondary)]">PIN: {viewingOrg.pincode}</p>}
                </div>
                <div>
                  <p className="text-[10px] uppercase font-bold text-[var(--color-secondary)] mb-1">Contact</p>
                  <p className="text-[var(--color-text-main)] font-medium">{viewingOrg.email || '—'}</p>
                  <p className="text-[var(--color-secondary)]">{viewingOrg.phone || '—'}</p>
                </div>
              </div>

              {viewingOrg.address && (
                <div>
                  <p className="text-[10px] uppercase font-bold text-[var(--color-secondary)] mb-1">Street Address</p>
                  <p className="text-[var(--color-text-main)]">{viewingOrg.address}</p>
                </div>
              )}
            </div>

            <div className="pt-6 mt-6 border-t border-[var(--color-border-subtle)] flex justify-end gap-2">
              <button
                type="button"
                onClick={() => {
                  setViewModalOpen(false);
                  handleOpenEdit(viewingOrg);
                }}
                className="px-4 py-2 rounded-xl bg-[var(--color-primary)] text-white text-xs font-bold hover:opacity-90"
              >
                Edit Organization
              </button>
              <button
                type="button"
                onClick={() => setViewModalOpen(false)}
                className="px-4 py-2 rounded-xl border border-[var(--color-border-subtle)] text-xs font-bold"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
