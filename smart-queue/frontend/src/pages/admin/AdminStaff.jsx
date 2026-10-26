import React, { useState, useEffect } from 'react';
import api from '../../services/api';

export default function AdminStaff() {
  const [staffList, setStaffList] = useState([]);
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
    email: '',
    name: '',
    organization_id: '',
    branch_id: '',
    status: 'ACTIVE'
  });
  const [modalBranches, setModalBranches] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [togglingStaffId, setTogglingStaffId] = useState(null);
  const [modalError, setModalError] = useState('');

  const loadData = async () => {
    try {
      setLoading(true);
      setError('');
      const [staffRes, orgsRes] = await Promise.all([
        api.get('/api/admin/staff', {
          params: {
            organization_id: selectedOrg || undefined,
            branch_id: selectedBranch || undefined,
            status: selectedStatus || undefined,
            search: searchTerm || undefined
          }
        }),
        api.get('/api/admin/organizations')
      ]);
      setStaffList(staffRes.data);
      setOrganizations(orgsRes.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load staff');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedOrg, selectedBranch, selectedStatus]);

  // When selectedOrg changes in filter, load branches for filter
  useEffect(() => {
    if (selectedOrg) {
      api.get(`/api/admin/branches?organization_id=${selectedOrg}`).then((res) => {
        setBranches(res.data);
      });
    } else {
      setBranches([]);
      setSelectedBranch('');
    }
  }, [selectedOrg]);

  // When organization changes in modal, load branches for modal
  const handleModalOrgChange = async (orgId) => {
    setFormData((prev) => ({ ...prev, organization_id: orgId, branch_id: '' }));
    if (orgId) {
      try {
        const res = await api.get(`/api/admin/branches?organization_id=${orgId}`);
        setModalBranches(res.data);
        if (res.data.length > 0) {
          setFormData((prev) => ({ ...prev, branch_id: res.data[0].id }));
        }
      } catch (err) {
        console.error(err);
      }
    } else {
      setModalBranches([]);
    }
  };

  const handleOpenAssign = async () => {
    setIsEditing(false);
    setCurrentId(null);
    const firstOrgId = organizations[0]?.id || '';
    setFormData({
      email: '',
      name: '',
      organization_id: firstOrgId,
      branch_id: '',
      status: 'ACTIVE'
    });
    setModalError('');
    if (firstOrgId) {
      const res = await api.get(`/api/admin/branches?organization_id=${firstOrgId}`);
      setModalBranches(res.data);
      if (res.data.length > 0) {
        setFormData((prev) => ({ ...prev, branch_id: res.data[0].id }));
      }
    }
    setModalOpen(true);
  };

  const handleOpenEdit = async (staff) => {
    setIsEditing(true);
    setCurrentId(staff.id);
    setFormData({
      email: staff.user_email || '',
      name: staff.user_name || '',
      organization_id: staff.organization_id,
      branch_id: staff.branch_id,
      status: staff.status
    });
    setModalError('');
    const res = await api.get(`/api/admin/branches?organization_id=${staff.organization_id}`);
    setModalBranches(res.data);
    setModalOpen(true);
  };

  const handleStatusToggle = async (staff) => {
    if (togglingStaffId) return;
    setTogglingStaffId(staff.id);
    const nextStatus = staff.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE';
    try {
      await api.patch(`/api/admin/staff/${staff.id}/status`, { status: nextStatus });
      await loadData();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to update staff status');
    } finally {
      setTogglingStaffId(null);
    }
  };

  const handleSubmitModal = async (e) => {
    e.preventDefault();
    if (submitting) return;
    if (!formData.organization_id || !formData.branch_id) {
      setModalError('Please select both an Organization and Branch');
      return;
    }

    setSubmitting(true);
    setModalError('');

    try {
      if (isEditing) {
        await api.put(`/api/admin/staff/${currentId}`, {
          organization_id: formData.organization_id,
          branch_id: formData.branch_id,
          status: formData.status
        });
      } else {
        await api.post('/api/admin/staff', {
          email: formData.email.trim(),
          name: formData.name.trim(),
          organization_id: formData.organization_id,
          branch_id: formData.branch_id
        });
      }
      setModalOpen(false);
      loadData();
    } catch (err) {
      setModalError(err.response?.data?.detail || 'Failed to save staff assignment');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto pb-12 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-bold uppercase tracking-widest text-[var(--color-primary)]">
            Human Resources
          </span>
          <h1 className="text-3xl font-extrabold tracking-tight text-[var(--color-text-main)] mt-1">
            Staff Management
          </h1>
          <p className="text-sm text-[var(--color-secondary)] mt-1">
            Assign staff members to authorized branches and enforce queue operator privileges.
          </p>
        </div>

        <button
          type="button"
          onClick={handleOpenAssign}
          className="self-start sm:self-auto px-5 py-2.5 bg-[var(--color-primary)] hover:opacity-90 text-white rounded-xl text-xs font-bold transition-all shadow-xs flex items-center gap-2"
        >
          <span>＋ Assign Staff</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-[var(--color-surface)] p-4 sm:p-5 rounded-[20px] border border-[var(--color-border-subtle)] flex flex-col md:flex-row gap-4 items-center justify-between">
        <div className="w-full md:w-80 flex items-center gap-2">
          <input
            type="text"
            placeholder="Search staff name or email..."
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
            className="px-3 py-2 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-input-bg)] text-xs text-[var(--color-text-main)]"
          >
            <option value="">All Organizations</option>
            {organizations.map((o) => (
              <option key={o.id} value={o.id}>
                {o.name}
              </option>
            ))}
          </select>

          {selectedOrg && (
            <select
              value={selectedBranch}
              onChange={(e) => setSelectedBranch(e.target.value)}
              className="px-3 py-2 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-input-bg)] text-xs text-[var(--color-text-main)]"
            >
              <option value="">All Branches</option>
              {branches.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.address}, {b.city}
                </option>
              ))}
            </select>
          )}

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
                <th className="px-6 py-4">Staff Member</th>
                <th className="px-6 py-4">Organization</th>
                <th className="px-6 py-4">Assigned Branch</th>
                <th className="px-6 py-4">Role</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-border-subtle)]">
              {loading && (
                <tr>
                  <td colSpan="6" className="text-center py-12 text-[var(--color-secondary)]">
                    Loading staff records...
                  </td>
                </tr>
              )}

              {!loading && staffList.length === 0 && (
                <tr>
                  <td colSpan="6" className="text-center py-12 text-[var(--color-secondary)]">
                    No staff records found. Click "+ Assign Staff" to assign branch operators.
                  </td>
                </tr>
              )}

              {!loading &&
                staffList.map((st) => (
                  <tr key={st.id} className="hover:bg-[var(--color-surface-hover)] transition-colors">
                    <td className="px-6 py-4">
                      <p className="font-bold text-[var(--color-text-main)] text-sm">{st.user_name}</p>
                      <p className="text-[11px] text-[var(--color-secondary)]">{st.user_email || '—'}</p>
                    </td>
                    <td className="px-6 py-4 font-semibold text-[var(--color-text-main)]">
                      {st.organization_name}
                    </td>
                    <td className="px-6 py-4 text-[var(--color-secondary)]">
                      📍 {st.branch_address}, {st.branch_city}
                    </td>
                    <td className="px-6 py-4">
                      <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-teal-100 text-teal-800 dark:bg-teal-950 dark:text-teal-300 uppercase">
                        {st.role}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                          st.status === 'ACTIVE'
                            ? 'bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-300'
                            : 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300'
                        }`}
                      >
                        {st.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right space-x-2">
                      <button
                        type="button"
                        onClick={() => handleOpenEdit(st)}
                        className="px-3 py-1.5 rounded-lg border border-[var(--color-border-subtle)] font-bold text-[11px] hover:bg-[var(--color-surface-hover)] text-[var(--color-text-main)] transition-colors"
                      >
                        Reassign Branch
                      </button>
                      <button
                        type="button"
                        disabled={togglingStaffId === st.id}
                        onClick={() => handleStatusToggle(st)}
                        className={`px-3 py-1.5 rounded-lg font-bold text-[11px] transition-colors disabled:opacity-50 ${
                          st.status === 'ACTIVE'
                            ? 'bg-orange-50 text-orange-700 dark:bg-orange-950/40 dark:text-orange-300 hover:bg-orange-100'
                            : 'bg-teal-50 text-teal-700 dark:bg-teal-950/40 dark:text-teal-300 hover:bg-teal-100'
                        }`}
                      >
                        {togglingStaffId === st.id ? 'Updating...' : st.status === 'ACTIVE' ? 'Deactivate' : 'Activate'}
                      </button>
                    </td>
                  </tr>
                ))}
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
                {isEditing ? 'Reassign Staff' : 'Assign New Staff'}
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
                  Staff Email *
                </label>
                <input
                  type="email"
                  required
                  disabled={isEditing}
                  placeholder="staff@organization.com"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-input-bg)] text-xs text-[var(--color-text-main)] disabled:opacity-60"
                />
              </div>

              {!isEditing && (
                <div>
                  <label className="block text-xs font-bold uppercase text-[var(--color-secondary)] mb-1">
                    Staff Name
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. John Operator"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-input-bg)] text-xs text-[var(--color-text-main)]"
                  />
                </div>
              )}

              <div>
                <label className="block text-xs font-bold uppercase text-[var(--color-secondary)] mb-1">
                  Organization *
                </label>
                <select
                  required
                  value={formData.organization_id}
                  onChange={(e) => handleModalOrgChange(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-input-bg)] text-xs text-[var(--color-text-main)]"
                >
                  <option value="">Select Organization</option>
                  {organizations.map((o) => (
                    <option key={o.id} value={o.id}>
                      {o.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-[var(--color-secondary)] mb-1">
                  Branch *
                </label>
                <select
                  required
                  value={formData.branch_id}
                  onChange={(e) => setFormData({ ...formData, branch_id: e.target.value })}
                  disabled={modalBranches.length === 0}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-input-bg)] text-xs text-[var(--color-text-main)] disabled:opacity-50"
                >
                  {modalBranches.length === 0 ? (
                    <option value="">No branches available for this organization</option>
                  ) : (
                    modalBranches.map((b) => (
                      <option key={b.id} value={b.id}>
                        {b.address}, {b.city}
                      </option>
                    ))
                  )}
                </select>
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
                  {submitting ? 'Saving...' : 'Save Staff Assignment'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
