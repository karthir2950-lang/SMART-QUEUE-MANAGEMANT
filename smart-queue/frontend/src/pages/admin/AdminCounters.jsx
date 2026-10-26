import React, { useState, useEffect } from 'react';
import api from '../../services/api';

export default function AdminCounters() {
  const [counters, setCounters] = useState([]);
  const [organizations, setOrganizations] = useState([]);
  const [branches, setBranches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Filters
  const [selectedOrg, setSelectedOrg] = useState('');
  const [selectedBranch, setSelectedBranch] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  // Modal
  const [modalOpen, setModalOpen] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [currentId, setCurrentId] = useState(null);
  const [formData, setFormData] = useState({
    branch_id: '',
    counter_number: 1,
    name: '',
    status: 'AVAILABLE'
  });
  const [modalBranches, setModalBranches] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [togglingCounterId, setTogglingCounterId] = useState(null);
  const [modalError, setModalError] = useState('');

  const loadData = async () => {
    try {
      setLoading(true);
      setError('');
      const [countersRes, orgsRes] = await Promise.all([
        api.get('/api/admin/counters', {
          params: {
            branch_id: selectedBranch || undefined,
            status: selectedStatus || undefined,
            search: searchTerm || undefined
          }
        }),
        api.get('/api/admin/organizations')
      ]);
      setCounters(countersRes.data);
      setOrganizations(orgsRes.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load counters');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedBranch, selectedStatus]);

  // Load branches when selectedOrg changes in filter
  useEffect(() => {
    const fetchBranches = async () => {
      if (!selectedOrg) {
        setBranches([]);
        setSelectedBranch('');
        return;
      }
      try {
        const res = await api.get('/api/admin/branches', {
          params: { organization_id: selectedOrg }
        });
        setBranches(res.data);
      } catch (err) {
        console.error('Failed to load branches for filter', err);
      }
    };
    fetchBranches();
  }, [selectedOrg]);

  // Load all active branches for modal
  const loadModalBranches = async () => {
    try {
      const res = await api.get('/api/admin/branches');
      setModalBranches(res.data);
    } catch (err) {
      console.error('Failed to load branches for modal', err);
    }
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    loadData();
  };

  const handleOpenCreateModal = () => {
    setIsEditing(false);
    setCurrentId(null);
    setFormData({
      branch_id: branches.length > 0 ? branches[0].id : '',
      counter_number: counters.length + 1,
      name: `Counter ${counters.length + 1}`,
      status: 'AVAILABLE'
    });
    setModalError('');
    loadModalBranches();
    setModalOpen(true);
  };

  const handleOpenEditModal = (counter) => {
    setIsEditing(true);
    setCurrentId(counter.id);
    setFormData({
      branch_id: counter.branch_id,
      counter_number: counter.counter_number,
      name: counter.name,
      status: counter.status
    });
    setModalError('');
    loadModalBranches();
    setModalOpen(true);
  };

  const handleModalSubmit = async (e) => {
    e.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    setModalError('');

    try {
      if (isEditing) {
        await api.put(`/api/admin/counters/${currentId}`, {
          counter_number: parseInt(formData.counter_number, 10),
          name: formData.name,
          status: formData.status
        });
      } else {
        await api.post('/api/admin/counters', {
          branch_id: formData.branch_id,
          counter_number: parseInt(formData.counter_number, 10),
          name: formData.name,
          status: formData.status
        });
      }
      setModalOpen(false);
      loadData();
    } catch (err) {
      setModalError(err.response?.data?.detail || 'Failed to save counter');
    } finally {
      setSubmitting(false);
    }
  };

  const handleStatusToggle = async (counter, newStatus) => {
    if (togglingCounterId) return;
    setTogglingCounterId(counter.id);
    try {
      await api.patch(`/api/admin/counters/${counter.id}/status`, {
        status: newStatus
      });
      await loadData();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to update counter status');
    } finally {
      setTogglingCounterId(null);
    }
  };

  // Metrics
  const totalCount = counters.length;
  const availableCount = counters.filter(c => c.status === 'AVAILABLE').length;
  const busyCount = counters.filter(c => c.status === 'BUSY').length;
  const closedCount = counters.filter(c => c.status === 'CLOSED').length;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--color-text-main)]">
            Service Counters Management
          </h1>
          <p className="text-xs text-[var(--color-secondary)] mt-1">
            Configure, deploy, and monitor physical service desks and teller windows
          </p>
        </div>
        <button
          onClick={handleOpenCreateModal}
          className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-[var(--color-primary)] text-white text-xs font-semibold hover:opacity-90 shadow-sm transition-all"
        >
          <span>➕</span>
          <span>Add New Counter</span>
        </button>
      </div>

      {/* Metrics Ribbon */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface)]">
          <p className="text-[11px] font-semibold text-[var(--color-secondary)] uppercase tracking-wider">Total Counters</p>
          <p className="text-2xl font-black text-[var(--color-text-main)] mt-1">{totalCount}</p>
        </div>
        <div className="p-4 rounded-xl border border-emerald-100 dark:border-emerald-950 bg-emerald-50/50 dark:bg-emerald-950/20">
          <p className="text-[11px] font-semibold text-emerald-700 dark:text-emerald-400 uppercase tracking-wider">Available</p>
          <p className="text-2xl font-black text-emerald-800 dark:text-emerald-300 mt-1">{availableCount}</p>
        </div>
        <div className="p-4 rounded-xl border border-amber-100 dark:border-amber-950 bg-amber-50/50 dark:bg-amber-950/20">
          <p className="text-[11px] font-semibold text-amber-700 dark:text-amber-400 uppercase tracking-wider">Busy / Serving</p>
          <p className="text-2xl font-black text-amber-800 dark:text-amber-300 mt-1">{busyCount}</p>
        </div>
        <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/40">
          <p className="text-[11px] font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">Closed</p>
          <p className="text-2xl font-black text-slate-800 dark:text-slate-300 mt-1">{closedCount}</p>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="p-4 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface)] flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
        <form onSubmit={handleSearchSubmit} className="flex-1 flex gap-2">
          <input
            type="text"
            placeholder="Search by counter name or number..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="flex-1 px-3.5 py-2 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-canvas)] text-xs text-[var(--color-text-main)] focus:outline-hidden focus:ring-2 focus:ring-[var(--color-primary)]"
          />
          <button
            type="submit"
            className="px-4 py-2 rounded-xl bg-[var(--color-canvas)] border border-[var(--color-border-subtle)] text-xs font-semibold text-[var(--color-text-main)] hover:bg-[var(--color-surface-hover)]"
          >
            Search
          </button>
        </form>

        <div className="flex flex-wrap gap-2 items-center">
          {/* Org Filter */}
          <select
            value={selectedOrg}
            onChange={(e) => setSelectedOrg(e.target.value)}
            className="px-3 py-2 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-canvas)] text-xs text-[var(--color-text-main)] focus:outline-hidden"
          >
            <option value="">All Organizations</option>
            {organizations.map((org) => (
              <option key={org.id} value={org.id}>{org.name}</option>
            ))}
          </select>

          {/* Branch Filter */}
          <select
            value={selectedBranch}
            onChange={(e) => setSelectedBranch(e.target.value)}
            disabled={!selectedOrg}
            className="px-3 py-2 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-canvas)] text-xs text-[var(--color-text-main)] focus:outline-hidden disabled:opacity-50"
          >
            <option value="">All Branches</option>
            {branches.map((b) => (
              <option key={b.id} value={b.id}>{b.city} • {b.name || b.address}</option>
            ))}
          </select>

          {/* Status Filter */}
          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="px-3 py-2 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-canvas)] text-xs text-[var(--color-text-main)] focus:outline-hidden"
          >
            <option value="">All Statuses</option>
            <option value="AVAILABLE">Available</option>
            <option value="BUSY">Busy</option>
            <option value="CLOSED">Closed</option>
          </select>

          {(selectedOrg || selectedBranch || selectedStatus || searchTerm) && (
            <button
              onClick={() => {
                setSelectedOrg('');
                setSelectedBranch('');
                setSelectedStatus('');
                setSearchTerm('');
                setTimeout(loadData, 0);
              }}
              className="text-xs text-[var(--color-primary)] hover:underline font-semibold px-2 py-1"
            >
              Reset
            </button>
          )}
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="p-4 rounded-xl border border-red-200 bg-red-50 text-red-700 text-xs">
          {error}
        </div>
      )}

      {/* Counters Grid / Table */}
      <div className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-surface)] overflow-hidden shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-[var(--color-border-subtle)] bg-[var(--color-canvas)] text-[11px] font-semibold text-[var(--color-secondary)] uppercase tracking-wider">
                <th className="py-3 px-4">Counter #</th>
                <th className="py-3 px-4">Name</th>
                <th className="py-3 px-4">Branch</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Created</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-border-subtle)] text-xs">
              {loading ? (
                <tr>
                  <td colSpan="6" className="py-8 text-center text-[var(--color-secondary)]">
                    Loading counters data...
                  </td>
                </tr>
              ) : counters.length === 0 ? (
                <tr>
                  <td colSpan="6" className="py-8 text-center text-[var(--color-secondary)]">
                    No counters found matching current filters.
                  </td>
                </tr>
              ) : (
                counters.map((c) => {
                  const isAvailable = c.status === 'AVAILABLE';
                  const isBusy = c.status === 'BUSY';
                  const isClosed = c.status === 'CLOSED';

                  return (
                    <tr key={c.id} className="hover:bg-[var(--color-canvas)]/50 transition-colors">
                      <td className="py-3.5 px-4 font-mono font-bold text-[var(--color-primary)]">
                        #{c.counter_number}
                      </td>
                      <td className="py-3.5 px-4 font-medium text-[var(--color-text-main)]">
                        {c.name}
                      </td>
                      <td className="py-3.5 px-4 text-[var(--color-secondary)]">
                        {c.branch_name || 'Branch Desk'}
                      </td>
                      <td className="py-3.5 px-4">
                        <span
                          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold ${
                            isAvailable
                              ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300'
                              : isBusy
                              ? 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300'
                              : 'bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300'
                          }`}
                        >
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${
                              isAvailable
                                ? 'bg-emerald-500'
                                : isBusy
                                ? 'bg-amber-500'
                                : 'bg-slate-400'
                            }`}
                          />
                          {c.status}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-[var(--color-secondary)]">
                        {c.created_at ? new Date(c.created_at).toLocaleDateString() : '—'}
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          {/* Quick Toggle Status */}
                          <select
                            value={c.status}
                            onChange={(e) => handleStatusToggle(c, e.target.value)}
                            className="px-2 py-1 text-[11px] font-semibold rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-canvas)] text-[var(--color-text-main)]"
                          >
                            <option value="AVAILABLE">Set Available</option>
                            <option value="BUSY">Set Busy</option>
                            <option value="CLOSED">Set Closed</option>
                          </select>

                          <button
                            type="button"
                            onClick={() => handleOpenEditModal(c)}
                            className="p-1.5 rounded-lg border border-[var(--color-border-subtle)] hover:bg-[var(--color-surface-hover)] text-[var(--color-secondary)] hover:text-[var(--color-text-main)]"
                            title="Edit Counter"
                          >
                            ✏️
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create / Edit Modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs">
          <div className="w-full max-w-md rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border-subtle)] shadow-2xl p-6">
            <div className="flex items-center justify-between pb-4 border-b border-[var(--color-border-subtle)]">
              <h3 className="text-base font-bold text-[var(--color-text-main)]">
                {isEditing ? 'Edit Service Counter' : 'Register New Counter'}
              </h3>
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                className="text-[var(--color-secondary)] hover:text-[var(--color-text-main)] text-sm"
              >
                ✕
              </button>
            </div>

            {modalError && (
              <div className="mt-4 p-3 rounded-xl border border-red-200 bg-red-50 text-red-700 text-xs">
                {modalError}
              </div>
            )}

            <form onSubmit={handleModalSubmit} className="mt-4 space-y-4">
              {!isEditing && (
                <div>
                  <label className="block text-xs font-semibold text-[var(--color-secondary)] mb-1">
                    Branch Assignment <span className="text-red-500">*</span>
                  </label>
                  <select
                    required
                    value={formData.branch_id}
                    onChange={(e) => setFormData({ ...formData, branch_id: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-canvas)] text-xs text-[var(--color-text-main)] focus:outline-hidden focus:ring-2 focus:ring-[var(--color-primary)]"
                  >
                    <option value="">Select Branch</option>
                    {modalBranches.map((b) => (
                      <option key={b.id} value={b.id}>
                        {b.city} — {b.address || b.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-[var(--color-secondary)] mb-1">
                    Counter Number <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="number"
                    min="1"
                    required
                    value={formData.counter_number}
                    onChange={(e) => setFormData({ ...formData, counter_number: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-canvas)] text-xs text-[var(--color-text-main)] focus:outline-hidden focus:ring-2 focus:ring-[var(--color-primary)]"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[var(--color-secondary)] mb-1">
                    Initial Status
                  </label>
                  <select
                    value={formData.status}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-canvas)] text-xs text-[var(--color-text-main)] focus:outline-hidden"
                  >
                    <option value="AVAILABLE">Available</option>
                    <option value="BUSY">Busy</option>
                    <option value="CLOSED">Closed</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-[var(--color-secondary)] mb-1">
                  Counter Name / Label <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Counter 1 - General Inquiries"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-canvas)] text-xs text-[var(--color-text-main)] focus:outline-hidden focus:ring-2 focus:ring-[var(--color-primary)]"
                />
              </div>

              <div className="pt-4 border-t border-[var(--color-border-subtle)] flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="px-4 py-2 rounded-xl border border-[var(--color-border-subtle)] text-xs font-semibold text-[var(--color-secondary)] hover:bg-[var(--color-surface-hover)]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 rounded-xl bg-[var(--color-primary)] text-white text-xs font-semibold hover:opacity-90 disabled:opacity-50"
                >
                  {submitting ? 'Saving...' : isEditing ? 'Save Changes' : 'Create Counter'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
