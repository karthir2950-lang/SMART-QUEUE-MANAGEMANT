import React, { useState, useEffect } from 'react';
import api from '../../services/api';

export default function AdminBranches() {
  const [branches, setBranches] = useState([]);
  const [organizations, setOrganizations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Filters
  const [selectedOrg, setSelectedOrg] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  // Modal
  const [modalOpen, setModalOpen] = useState(false);
  const [viewModalOpen, setViewModalOpen] = useState(false);
  const [viewingBranch, setViewingBranch] = useState(null);
  const [togglingStatusId, setTogglingStatusId] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [currentId, setCurrentId] = useState(null);
  const [formData, setFormData] = useState({
    organization_id: '',
    address: '',
    city: '',
    state: '',
    pincode: '',
    phone: '',
    opening_time: '08:00',
    closing_time: '20:00',
    status: 'ACTIVE'
  });
  const [submitting, setSubmitting] = useState(false);
  const [modalError, setModalError] = useState('');

  const loadData = async () => {
    try {
      setLoading(true);
      setError('');
      const [branchesRes, orgsRes] = await Promise.all([
        api.get('/api/admin/branches', {
          params: {
            organization_id: selectedOrg || undefined,
            status: selectedStatus || undefined,
            search: searchTerm || undefined
          }
        }),
        api.get('/api/admin/organizations')
      ]);
      setBranches(branchesRes.data);
      setOrganizations(orgsRes.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load branches');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedOrg, selectedStatus]);

  const handleOpenCreate = () => {
    setIsEditing(false);
    setCurrentId(null);
    setFormData({
      organization_id: organizations[0]?.id || '',
      address: '',
      city: '',
      state: '',
      pincode: '',
      phone: '',
      opening_time: '08:00',
      closing_time: '20:00',
      status: 'ACTIVE'
    });
    setModalError('');
    setModalOpen(true);
  };

  const handleOpenEdit = (branch) => {
    setIsEditing(true);
    setCurrentId(branch.id);
    setFormData({
      organization_id: branch.organization_id,
      address: branch.address,
      city: branch.city,
      state: branch.state,
      pincode: branch.pincode || '',
      phone: branch.phone || '',
      opening_time: branch.opening_time ? branch.opening_time.substring(0, 5) : '08:00',
      closing_time: branch.closing_time ? branch.closing_time.substring(0, 5) : '20:00',
      status: branch.status
    });
    setModalError('');
    setModalOpen(true);
  };

  const handleOpenView = (branch) => {
    setViewingBranch(branch);
    setViewModalOpen(true);
  };

  const handleStatusToggle = async (branch) => {
    if (togglingStatusId) return;
    setTogglingStatusId(branch.id);
    const nextStatus = branch.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE';
    try {
      await api.patch(`/api/admin/branches/${branch.id}/status`, { status: nextStatus });
      await loadData();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to update branch status');
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
        await api.put(`/api/admin/branches/${currentId}`, formData);
      } else {
        await api.post('/api/admin/branches', formData);
      }
      setModalOpen(false);
      loadData();
    } catch (err) {
      setModalError(err.response?.data?.detail || 'Failed to save branch');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto pb-12 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-bold uppercase tracking-widest text-[var(--color-primary)]">
            Locations
          </span>
          <h1 className="text-3xl font-extrabold tracking-tight text-[var(--color-text-main)] mt-1">
            Branches
          </h1>
          <p className="text-sm text-[var(--color-secondary)] mt-1">
            Manage organization branch locations, operational hours, and active status.
          </p>
        </div>

        <button
          type="button"
          onClick={handleOpenCreate}
          className="self-start sm:self-auto px-5 py-2.5 bg-[var(--color-primary)] hover:opacity-90 text-white rounded-xl text-xs font-bold transition-all shadow-xs flex items-center gap-2"
        >
          <span>＋ Add Branch</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-[var(--color-surface)] p-4 sm:p-5 rounded-[20px] border border-[var(--color-border-subtle)] flex flex-col md:flex-row gap-4 items-center justify-between">
        <div className="w-full md:w-80 flex items-center gap-2">
          <input
            type="text"
            placeholder="Search address or city..."
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
            value={selectedOrg}
            onChange={(e) => setSelectedOrg(e.target.value)}
            className="px-3 py-2 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-input-bg)] text-xs text-[var(--color-text-main)] max-w-xs"
          >
            <option value="">All Organizations</option>
            {organizations.map((o) => (
              <option key={o.id} value={o.id}>
                {o.name}
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
                <th className="px-6 py-4">Branch Address</th>
                <th className="px-6 py-4">Organization</th>
                <th className="px-6 py-4">City / State</th>
                <th className="px-6 py-4">Hours</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-border-subtle)]">
              {loading && (
                <tr>
                  <td colSpan="6" className="text-center py-12 text-[var(--color-secondary)]">
                    Loading branches...
                  </td>
                </tr>
              )}

              {!loading && branches.length === 0 && (
                <tr>
                  <td colSpan="6" className="text-center py-12 text-[var(--color-secondary)]">
                    No branches found matching criteria.
                  </td>
                </tr>
              )}

              {!loading &&
                branches.map((b) => {
                  const org = organizations.find((o) => o.id === b.organization_id);
                  return (
                    <tr key={b.id} className="hover:bg-[var(--color-surface-hover)] transition-colors">
                      <td className="px-6 py-4 font-bold text-[var(--color-text-main)] text-sm">
                        {b.address}
                      </td>
                      <td className="px-6 py-4 font-semibold text-[var(--color-primary)]">
                        {org?.name || 'Organization'}
                      </td>
                      <td className="px-6 py-4 text-[var(--color-secondary)]">
                        {b.city}, {b.state} {b.pincode ? `(${b.pincode})` : ''}
                      </td>
                      <td className="px-6 py-4 text-[var(--color-secondary)]">
                        {b.opening_time ? `${b.opening_time.substring(0, 5)} - ${b.closing_time ? b.closing_time.substring(0, 5) : '20:00'}` : 'All Day'}
                      </td>
                      <td className="px-6 py-4">
                        <span
                          className={`px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                            b.status === 'ACTIVE'
                              ? 'bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-300'
                              : 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300'
                          }`}
                        >
                          {b.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right space-x-2">
                        <button
                          type="button"
                          onClick={() => handleOpenView(b)}
                          className="px-3 py-1.5 rounded-lg border border-[var(--color-border-subtle)] font-bold text-[11px] hover:bg-[var(--color-surface-hover)] text-[var(--color-text-main)] transition-colors"
                        >
                          View
                        </button>
                        <button
                          type="button"
                          onClick={() => handleOpenEdit(b)}
                          className="px-3 py-1.5 rounded-lg border border-[var(--color-border-subtle)] font-bold text-[11px] hover:bg-[var(--color-surface-hover)] text-[var(--color-text-main)] transition-colors"
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          disabled={togglingStatusId === b.id}
                          onClick={() => handleStatusToggle(b)}
                          className={`px-3 py-1.5 rounded-lg font-bold text-[11px] transition-colors disabled:opacity-50 ${
                            b.status === 'ACTIVE'
                              ? 'bg-orange-50 text-orange-700 dark:bg-orange-950/40 dark:text-orange-300 hover:bg-orange-100'
                              : 'bg-teal-50 text-teal-700 dark:bg-teal-950/40 dark:text-teal-300 hover:bg-teal-100'
                          }`}
                        >
                          {togglingStatusId === b.id ? 'Updating...' : b.status === 'ACTIVE' ? 'Deactivate' : 'Activate'}
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
          <div className="bg-[var(--color-surface)] w-full max-w-lg rounded-[24px] border border-[var(--color-border-subtle)] p-6 sm:p-8 shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-4 border-b border-[var(--color-border-subtle)] mb-6">
              <h3 className="text-lg font-bold text-[var(--color-text-main)]">
                {isEditing ? 'Edit Branch' : 'Create Branch'}
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
                  Organization *
                </label>
                <select
                  required
                  value={formData.organization_id}
                  onChange={(e) => setFormData({ ...formData, organization_id: e.target.value })}
                  disabled={isEditing}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-input-bg)] text-xs text-[var(--color-text-main)]"
                >
                  {organizations.map((o) => (
                    <option key={o.id} value={o.id}>
                      {o.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-[var(--color-secondary)] mb-1">
                  Branch Street Address *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. 124 Greams Road"
                  value={formData.address}
                  onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-input-bg)] text-xs text-[var(--color-text-main)]"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold uppercase text-[var(--color-secondary)] mb-1">
                    City *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.city}
                    onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-input-bg)] text-xs text-[var(--color-text-main)]"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase text-[var(--color-secondary)] mb-1">
                    State *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.state}
                    onChange={(e) => setFormData({ ...formData, state: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-input-bg)] text-xs text-[var(--color-text-main)]"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold uppercase text-[var(--color-secondary)] mb-1">
                    Pincode
                  </label>
                  <input
                    type="text"
                    value={formData.pincode}
                    onChange={(e) => setFormData({ ...formData, pincode: e.target.value })}
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

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold uppercase text-[var(--color-secondary)] mb-1">
                    Opening Time
                  </label>
                  <input
                    type="time"
                    value={formData.opening_time}
                    onChange={(e) => setFormData({ ...formData, opening_time: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-input-bg)] text-xs text-[var(--color-text-main)]"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase text-[var(--color-secondary)] mb-1">
                    Closing Time
                  </label>
                  <input
                    type="time"
                    value={formData.closing_time}
                    onChange={(e) => setFormData({ ...formData, closing_time: e.target.value })}
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
                  {submitting ? 'Saving...' : 'Save Branch'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      {/* View Branch Details Modal */}
      {viewModalOpen && viewingBranch && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-[var(--color-surface)] w-full max-w-lg rounded-[24px] border border-[var(--color-border-subtle)] p-6 sm:p-8 shadow-2xl">
            <div className="flex items-center justify-between pb-4 border-b border-[var(--color-border-subtle)] mb-6">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--color-primary)]">Branch Details</span>
                <h3 className="text-xl font-bold text-[var(--color-text-main)] mt-0.5">{viewingBranch.address}</h3>
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
                  <p className="text-[10px] uppercase font-bold text-[var(--color-secondary)]">Parent Organization</p>
                  <p className="font-semibold text-sm text-[var(--color-primary)] mt-0.5">
                    {organizations.find((o) => o.id === viewingBranch.organization_id)?.name || 'Organization'}
                  </p>
                </div>
                <div className="bg-[var(--color-canvas)] p-3 rounded-xl border border-[var(--color-border-subtle)]">
                  <p className="text-[10px] uppercase font-bold text-[var(--color-secondary)]">Status</p>
                  <span
                    className={`inline-block px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider mt-1 ${
                      viewingBranch.status === 'ACTIVE'
                        ? 'bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-300'
                        : 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300'
                    }`}
                  >
                    {viewingBranch.status}
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <p className="text-[10px] uppercase font-bold text-[var(--color-secondary)] mb-1">City & State</p>
                  <p className="text-[var(--color-text-main)] font-medium">
                    {viewingBranch.city}, {viewingBranch.state}
                  </p>
                  {viewingBranch.pincode && <p className="text-[var(--color-secondary)]">PIN: {viewingBranch.pincode}</p>}
                </div>
                <div>
                  <p className="text-[10px] uppercase font-bold text-[var(--color-secondary)] mb-1">Phone</p>
                  <p className="text-[var(--color-text-main)] font-medium">{viewingBranch.phone || '—'}</p>
                </div>
              </div>

              <div className="p-3 rounded-xl bg-[var(--color-canvas)] border border-[var(--color-border-subtle)]">
                <p className="text-[10px] uppercase font-bold text-[var(--color-secondary)] mb-1">Operating Hours</p>
                <p className="text-[var(--color-text-main)] font-medium">
                  {viewingBranch.opening_time ? `${viewingBranch.opening_time.substring(0, 5)} - ${viewingBranch.closing_time ? viewingBranch.closing_time.substring(0, 5) : '20:00'}` : 'All Day'}
                </p>
              </div>
            </div>

            <div className="pt-6 mt-6 border-t border-[var(--color-border-subtle)] flex justify-end gap-2">
              <button
                type="button"
                onClick={() => {
                  setViewModalOpen(false);
                  handleOpenEdit(viewingBranch);
                }}
                className="px-4 py-2 rounded-xl bg-[var(--color-primary)] text-white text-xs font-bold hover:opacity-90"
              >
                Edit Branch
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
