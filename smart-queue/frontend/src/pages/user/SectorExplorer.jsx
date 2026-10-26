import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import api from '../../services/api';
import { useAuth } from '../../context/AuthContext';

export default function SectorExplorer() {
  const { sectorSlug } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [sector, setSector] = useState(null);
  const [organizations, setOrganizations] = useState([]);
  const [branches, setBranches] = useState([]);
  const [services, setServices] = useState([]);
  const [availableSlots, setAvailableSlots] = useState([]);

  // Controlled single-selection state
  const [selectedOrgId, setSelectedOrgId] = useState('');
  const [selectedBranchId, setSelectedBranchId] = useState('');
  const [selectedServiceId, setSelectedServiceId] = useState('');
  const [selectedDate, setSelectedDate] = useState('');
  const [selectedTime, setSelectedTime] = useState('');

  // Status indicators
  const [loadingSector, setLoadingSector] = useState(true);
  const [loadingOrgs, setLoadingOrgs] = useState(false);
  const [loadingBranches, setLoadingBranches] = useState(false);
  const [loadingServices, setLoadingServices] = useState(false);
  const [loadingSlots, setLoadingSlots] = useState(false);
  const [isSubmittingBooking, setIsSubmittingBooking] = useState(false);

  const [error, setError] = useState('');

  // 1. Fetch Sector by Slug
  useEffect(() => {
    let active = true;
    const fetchSector = async () => {
      setLoadingSector(true);
      setError('');
      try {
        const res = await api.get(`/api/sectors/${sectorSlug}`);
        if (active) {
          setSector(res.data);
        }
      } catch (err) {
        if (active) {
          setError(`Sector "${sectorSlug}" not found or unavailable.`);
        }
      } finally {
        if (active) setLoadingSector(false);
      }
    };

    fetchSector();
    return () => {
      active = false;
    };
  }, [sectorSlug]);

  // 2. Fetch Organizations strictly filtered by Sector ID
  useEffect(() => {
    if (!sector?.id) return;
    let active = true;
    const fetchOrgs = async () => {
      setLoadingOrgs(true);
      try {
        const res = await api.get(`/api/organizations?sector_id=${sector.id}`);
        if (active) {
          const activeOrgs = (res.data || []).filter((o) => !o.status || o.status === 'ACTIVE');
          setOrganizations(activeOrgs);
        }
      } catch (_err) {
        if (active) setError('Failed to load organizations for this sector.');
      } finally {
        if (active) setLoadingOrgs(false);
      }
    };

    fetchOrgs();
    return () => {
      active = false;
    };
  }, [sector?.id]);

  // 3. Fetch Branches strictly filtered by Organization ID
  useEffect(() => {
    if (!selectedOrgId) {
      setBranches([]);
      setSelectedBranchId('');
      return;
    }

    let active = true;
    const fetchBranches = async () => {
      setLoadingBranches(true);
      try {
        const res = await api.get(`/api/branches?organization_id=${selectedOrgId}`);
        if (active) {
          const activeBranches = (res.data || []).filter((b) => !b.status || b.status === 'ACTIVE');
          setBranches(activeBranches);
        }
      } catch (_err) {
        if (active) setError('Failed to load branches for the selected organization.');
      } finally {
        if (active) setLoadingBranches(false);
      }
    };

    fetchBranches();
    return () => {
      active = false;
    };
  }, [selectedOrgId]);

  // 4. Fetch Services strictly filtered by Sector ID
  useEffect(() => {
    if (!sector?.id || !selectedBranchId) {
      setServices([]);
      setSelectedServiceId('');
      return;
    }

    let active = true;
    const fetchServices = async () => {
      setLoadingServices(true);
      try {
        const res = await api.get(`/api/services?sector_id=${sector.id}`);
        if (active) {
          const activeServices = (res.data || []).filter((s) => !s.status || s.status === 'ACTIVE');
          setServices(activeServices);
        }
      } catch (_err) {
        if (active) setError('Failed to load services for this sector.');
      } finally {
        if (active) setLoadingServices(false);
      }
    };

    fetchServices();
    return () => {
      active = false;
    };
  }, [sector?.id, selectedBranchId]);

  // 5. Fetch Available Slots
  useEffect(() => {
    if (!selectedBranchId || !selectedServiceId || !selectedDate) {
      setAvailableSlots([]);
      setSelectedTime('');
      return;
    }

    let active = true;
    const fetchSlots = async () => {
      setLoadingSlots(true);
      try {
        const res = await api.get('/api/appointments/available-slots', {
          params: {
            branch_id: selectedBranchId,
            service_id: selectedServiceId,
            appointment_date: selectedDate
          }
        });
        if (active) {
          setAvailableSlots(res.data);
        }
      } catch (err) {
        if (active) setError('Failed to load available appointment time slots.');
      } finally {
        if (active) setLoadingSlots(false);
      }
    };

    fetchSlots();
    return () => {
      active = false;
    };
  }, [selectedBranchId, selectedServiceId, selectedDate]);

  // Handlers for single selection
  const handleSelectOrg = (orgId) => {
    if (selectedOrgId === orgId) return;
    setSelectedOrgId(orgId);
    setSelectedBranchId('');
    setSelectedServiceId('');
    setSelectedDate('');
    setSelectedTime('');
  };

  const handleSelectBranch = (branchId) => {
    if (selectedBranchId === branchId) return;
    setSelectedBranchId(branchId);
    setSelectedServiceId('');
    setSelectedDate('');
    setSelectedTime('');
  };

  const handleSelectService = (serviceId) => {
    if (selectedServiceId === serviceId) return;
    setSelectedServiceId(serviceId);
    setSelectedDate('');
    setSelectedTime('');
  };

  const handleSelectTime = (slotTime) => {
    setSelectedTime(slotTime);
  };

  // Submit Booking with Double-Submit Lock
  const handleConfirmBooking = async () => {
    if (isSubmittingBooking) return;
    if (!sector?.id || !selectedOrgId || !selectedBranchId || !selectedServiceId || !selectedDate || !selectedTime) {
      setError('Please complete all selections before booking.');
      return;
    }

    setIsSubmittingBooking(true);
    setError('');

    try {
      const payload = {
        sector_id: sector.id,
        organization_id: selectedOrgId,
        branch_id: selectedBranchId,
        service_id: selectedServiceId,
        appointment_date: selectedDate,
        appointment_time: selectedTime,
        notes: `Booked via Sector Hub: ${sector.name}`
      };

      const res = await api.post('/api/appointments', payload);
      const apptId = res.data.id;

      // Issue digital queue token immediately
      await api.post(`/api/queue/token/${apptId}`);
      navigate(`/user/token/${apptId}`);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to book appointment. Please try another slot.');
      setIsSubmittingBooking(false);
    }
  };

  if (loadingSector) {
    return (
      <div className="max-w-4xl mx-auto py-12 text-center text-[var(--color-secondary)]">
        <div className="w-8 h-8 border-3 border-[var(--color-primary)] border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
        <p className="text-sm font-medium">Loading sector details...</p>
      </div>
    );
  }

  if (error && !sector) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="p-6 rounded-[20px] bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900/60 text-red-700 dark:text-red-400">
          <h2 className="text-lg font-bold mb-2">Sector Not Found</h2>
          <p className="text-sm mb-4">{error}</p>
          <Link to="/user/dashboard" className="inline-flex px-4 py-2 bg-[var(--color-primary)] text-white font-semibold rounded-xl text-sm">
            ← Return to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto pb-12">
      {/* Breadcrumb & Navigation */}
      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[var(--color-secondary)] mb-4">
        <Link to="/user/dashboard" className="hover:text-[var(--color-primary)] transition-colors">
          Hub
        </Link>
        <span>/</span>
        <span className="text-[var(--color-primary)]">{sector.name}</span>
      </div>

      {/* Sector Header Banner */}
      <div className="bg-[var(--color-surface)] p-6 sm:p-8 rounded-[22px] border border-[var(--color-border-subtle)] shadow-xs mb-8">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-[var(--color-text-main)]">
              {sector.name}
            </h1>
            <p className="text-sm text-[var(--color-secondary)] mt-1">
              {sector.description || `Verified organizations and queue management for ${sector.name}.`}
            </p>
          </div>
          <Link
            to="/user/dashboard"
            className="self-start sm:self-auto text-xs font-semibold px-3.5 py-2 rounded-xl border border-[var(--color-border-subtle)] hover:bg-[var(--color-surface-hover)] text-[var(--color-secondary)] hover:text-[var(--color-text-main)] transition-colors"
          >
            ← Switch Sector
          </Link>
        </div>
      </div>

      {/* Global Error Banner */}
      {error && (
        <div className="mb-6 p-4 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900/60 text-red-700 dark:text-red-400 text-sm font-medium">
          {error}
        </div>
      )}

      {/* STEP 1: ORGANIZATIONS */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-[var(--color-text-main)] flex items-center gap-2">
            <span className="w-6 h-6 rounded-full bg-[var(--color-primary)] text-white text-xs flex items-center justify-center font-bold">
              1
            </span>
            Select Organization
          </h2>
          {selectedOrgId && (
            <span className="text-xs text-[var(--color-primary)] font-semibold">1 Selected</span>
          )}
        </div>

        {loadingOrgs && (
          <div className="p-8 text-center text-sm text-[var(--color-secondary)] bg-[var(--color-surface)] rounded-[18px] border border-[var(--color-border-subtle)]">
            Loading organizations...
          </div>
        )}

        {!loadingOrgs && organizations.length === 0 && (
          <div className="p-8 text-center bg-[var(--color-surface)] rounded-[18px] border border-[var(--color-border-subtle)] text-[var(--color-secondary)]">
            <p className="font-semibold text-base mb-1">No organizations available for this sector.</p>
            <p className="text-xs">Please check back later or choose another sector from the hub.</p>
          </div>
        )}

        {!loadingOrgs && organizations.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {organizations.map((org) => {
              const isSelected = selectedOrgId === org.id;
              return (
                <div
                  key={org.id}
                  onClick={() => handleSelectOrg(org.id)}
                  className={`p-5 rounded-[18px] border cursor-pointer transition-all ${
                    isSelected
                      ? 'border-[var(--color-primary)] bg-[var(--color-accent-subtle)] shadow-xs'
                      : 'border-[var(--color-border-subtle)] bg-[var(--color-surface)] hover:border-[var(--color-primary)]'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-bold text-base text-[var(--color-text-main)]">{org.name}</h3>
                      <p className="text-xs text-[var(--color-secondary)] mt-1 line-clamp-2">
                        {org.description || org.address || 'Verified Organization'}
                      </p>
                    </div>
                    <span
                      className={`w-5 h-5 rounded-full border flex items-center justify-center text-xs transition-colors ${
                        isSelected
                          ? 'border-[var(--color-primary)] bg-[var(--color-primary)] text-white'
                          : 'border-[var(--color-border-subtle)] text-transparent'
                      }`}
                    >
                      ✓
                    </span>
                  </div>
                  {org.city && (
                    <div className="mt-3 pt-3 border-t border-[var(--color-border-subtle)] text-[11px] font-medium text-[var(--color-secondary)] flex items-center gap-1">
                      <span>📍</span>
                      <span>{org.city}{org.state ? `, ${org.state}` : ''}</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* STEP 2: BRANCHES (Only if Org is selected) */}
      {selectedOrgId && (
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold text-[var(--color-text-main)] flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-[var(--color-primary)] text-white text-xs flex items-center justify-center font-bold">
                2
              </span>
              Select Branch
            </h2>
            {selectedBranchId && (
              <span className="text-xs text-[var(--color-primary)] font-semibold">1 Selected</span>
            )}
          </div>

          {loadingBranches && (
            <div className="p-8 text-center text-sm text-[var(--color-secondary)] bg-[var(--color-surface)] rounded-[18px] border border-[var(--color-border-subtle)]">
              Loading branches...
            </div>
          )}

          {!loadingBranches && branches.length === 0 && (
            <div className="p-8 text-center bg-[var(--color-surface)] rounded-[18px] border border-[var(--color-border-subtle)] text-[var(--color-secondary)]">
              <p className="font-semibold text-base mb-1">No active branches found for this organization.</p>
            </div>
          )}

          {!loadingBranches && branches.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {branches.map((b) => {
                const isSelected = selectedBranchId === b.id;
                return (
                  <div
                    key={b.id}
                    onClick={() => handleSelectBranch(b.id)}
                    className={`p-5 rounded-[18px] border cursor-pointer transition-all ${
                      isSelected
                        ? 'border-[var(--color-primary)] bg-[var(--color-accent-subtle)] shadow-xs'
                        : 'border-[var(--color-border-subtle)] bg-[var(--color-surface)] hover:border-[var(--color-primary)]'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="font-bold text-sm text-[var(--color-text-main)]">{b.address}</h3>
                        <p className="text-xs text-[var(--color-secondary)] mt-1">
                          {b.city}, {b.state} {b.pincode ? `- ${b.pincode}` : ''}
                        </p>
                      </div>
                      <span
                        className={`w-5 h-5 rounded-full border flex items-center justify-center text-xs transition-colors ${
                          isSelected
                            ? 'border-[var(--color-primary)] bg-[var(--color-primary)] text-white'
                            : 'border-[var(--color-border-subtle)] text-transparent'
                        }`}
                      >
                        ✓
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* STEP 3: SERVICES (Only if Branch is selected) */}
      {selectedBranchId && (
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold text-[var(--color-text-main)] flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-[var(--color-primary)] text-white text-xs flex items-center justify-center font-bold">
                3
              </span>
              Select Service ({sector.name} Only)
            </h2>
            {selectedServiceId && (
              <span className="text-xs text-[var(--color-primary)] font-semibold">1 Selected</span>
            )}
          </div>

          {loadingServices && (
            <div className="p-8 text-center text-sm text-[var(--color-secondary)] bg-[var(--color-surface)] rounded-[18px] border border-[var(--color-border-subtle)]">
              Loading verified services...
            </div>
          )}

          {!loadingServices && services.length === 0 && (
            <div className="p-8 text-center bg-[var(--color-surface)] rounded-[18px] border border-[var(--color-border-subtle)] text-[var(--color-secondary)]">
              <p className="font-semibold text-base mb-1">No services configured for this sector.</p>
            </div>
          )}

          {!loadingServices && services.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
              {services.map((svc) => {
                const isSelected = selectedServiceId === svc.id;
                return (
                  <button
                    type="button"
                    key={svc.id}
                    onClick={() => handleSelectService(svc.id)}
                    className={`p-4 rounded-[16px] border text-left cursor-pointer transition-all flex flex-col justify-between ${
                      isSelected
                        ? 'border-[var(--color-primary)] bg-[var(--color-accent-subtle)] shadow-xs'
                        : 'border-[var(--color-border-subtle)] bg-[var(--color-surface)] hover:border-[var(--color-primary)]'
                    }`}
                  >
                    <div>
                      <h4 className="font-bold text-sm text-[var(--color-text-main)]">{svc.name}</h4>
                      <p className="text-[11px] text-[var(--color-secondary)] mt-1">
                        Est. {svc.average_service_time} mins
                      </p>
                    </div>
                    <span className="text-xs font-semibold text-[var(--color-primary)] mt-3">
                      {isSelected ? '✓ Selected' : 'Choose'}
                    </span>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* STEP 4: DATE & TIME SLOTS */}
      {selectedServiceId && (
        <div className="mb-8 bg-[var(--color-surface)] p-6 sm:p-8 rounded-[22px] border border-[var(--color-border-subtle)]">
          <h2 className="text-lg font-bold text-[var(--color-text-main)] mb-6 flex items-center gap-2">
            <span className="w-6 h-6 rounded-full bg-[var(--color-primary)] text-white text-xs flex items-center justify-center font-bold">
              4
            </span>
            Choose Date & Arrival Window
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-[var(--color-secondary)] mb-2">
                Select Date
              </label>
              <input
                type="date"
                min={new Date().toISOString().split('T')[0]}
                value={selectedDate}
                onChange={(e) => {
                  setSelectedDate(e.target.value);
                  setSelectedTime('');
                }}
                className="w-full px-4 py-3 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--color-input-bg)] text-[var(--color-text-main)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] text-sm"
              />
              <p className="text-xs text-[var(--color-secondary)] mt-2">
                Arrival windows will calculate estimated wait times upon booking.
              </p>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-[var(--color-secondary)] mb-2">
                Available Windows
              </label>

              {!selectedDate && (
                <div className="p-4 rounded-xl border border-dashed border-[var(--color-border-subtle)] text-xs text-[var(--color-secondary)] text-center">
                  Select a date to check available slots
                </div>
              )}

              {loadingSlots && (
                <div className="p-4 text-center text-xs text-[var(--color-secondary)]">
                  Checking real-time capacity...
                </div>
              )}

              {!loadingSlots && selectedDate && availableSlots.length === 0 && (
                <div className="p-4 rounded-xl bg-orange-50 dark:bg-orange-950/40 text-orange-700 dark:text-orange-300 text-xs font-medium border border-orange-200 dark:border-orange-900/60 text-center">
                  All slots are booked for this date. Please pick a different date.
                </div>
              )}

              {!loadingSlots && availableSlots.length > 0 && (
                <div className="grid grid-cols-3 gap-2 max-h-48 overflow-y-auto pr-1">
                  {availableSlots.map((timeStr) => {
                    const isSelected = selectedTime === timeStr;
                    return (
                      <button
                        type="button"
                        key={timeStr}
                        onClick={() => handleSelectTime(timeStr)}
                        className={`py-2 px-3 rounded-lg text-xs font-semibold border transition-all ${
                          isSelected
                            ? 'bg-[var(--color-primary)] text-white border-[var(--color-primary)] shadow-xs'
                            : 'bg-[var(--color-surface)] text-[var(--color-text-main)] border-[var(--color-border-subtle)] hover:border-[var(--color-primary)]'
                        }`}
                      >
                        {timeStr.substring(0, 5)}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* STEP 5: VISITOR CONFIRMATION & BOOKING ACTION */}
      {selectedTime && (
        <div className="bg-[var(--color-surface)] p-6 sm:p-8 rounded-[22px] border border-[var(--color-border-subtle)] shadow-xs">
          <h2 className="text-lg font-bold text-[var(--color-text-main)] mb-4 flex items-center gap-2">
            <span className="w-6 h-6 rounded-full bg-[var(--color-primary)] text-white text-xs flex items-center justify-center font-bold">
              5
            </span>
            Confirm Your Booking
          </h2>

          <div className="p-4 rounded-xl bg-[var(--color-accent-subtle)] border border-[#CDE5E7] dark:border-teal-900/40 mb-6 flex items-start gap-3 text-xs leading-relaxed text-[var(--color-text-main)]">
            <span className="text-base leading-none mt-0.5 text-[var(--color-primary)]">ℹ️</span>
            <div>
              <p className="font-bold mb-1">Queue Arrival Window Notice</p>
              <p className="text-[var(--color-secondary)]">
                Your selected arrival window is <strong>{selectedDate}</strong> at <strong>{selectedTime.substring(0, 5)}</strong>. A digital QR token will be generated immediately with real-time queue position and waiting estimation.
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={handleConfirmBooking}
            disabled={isSubmittingBooking}
            className="w-full py-4 px-6 bg-[var(--color-primary)] hover:opacity-90 active:scale-[0.99] text-white rounded-xl font-bold text-sm transition-all shadow-sm flex items-center justify-center gap-2 disabled:opacity-50 disabled:pointer-events-none"
          >
            {isSubmittingBooking ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                <span>Processing Appointment...</span>
              </>
            ) : (
              <span>Confirm & Issue Token →</span>
            )}
          </button>
        </div>
      )}
    </div>
  );
}
