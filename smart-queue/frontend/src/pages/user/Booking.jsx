import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../../services/api';
import { useAuth } from '../../context/AuthContext';

export default function Booking() {
  const { sectorId } = useParams();
  const navigate = useNavigate();
  const { user, profile } = useAuth();
  
  const [organizations, setOrganizations] = useState([]);
  const [branches, setBranches] = useState([]);
  const [services, setServices] = useState([]);
  const [availableSlots, setAvailableSlots] = useState([]);
  
  const [selectedOrg, setSelectedOrg] = useState('');
  const [selectedBranch, setSelectedBranch] = useState('');
  const [selectedService, setSelectedService] = useState('');
  const [selectedDate, setSelectedDate] = useState('');
  const [selectedTime, setSelectedTime] = useState('');
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // 1. Fetch Organizations on load
  useEffect(() => {
    if (sectorId) {
      api.get(`/api/organizations?sector_id=${sectorId}`)
        .then(res => setOrganizations(res.data))
        .catch(err => console.error(err));
    }
  }, [sectorId]);

  // 2. Fetch Branches when Org changes
  useEffect(() => {
    if (selectedOrg) {
      api.get(`/api/branches?organization_id=${selectedOrg}`)
        .then(res => setBranches(res.data))
        .catch(err => console.error(err));
    } else {
      setBranches([]);
    }
  }, [selectedOrg]);

  // 3. Fetch Services when Branch changes
  useEffect(() => {
    if (sectorId && selectedBranch) {
      // In this system, services are tied to sectors, but we fetch them once branch is selected
      api.get(`/api/services?sector_id=${sectorId}`)
        .then(res => setServices(res.data))
        .catch(err => console.error(err));
    } else {
      setServices([]);
    }
  }, [sectorId, selectedBranch]);

  // 4. Fetch Available Slots when Date/Service changes
  useEffect(() => {
    if (selectedBranch && selectedService && selectedDate) {
      setLoading(true);
      api.get(`/api/appointments/available-slots`, {
        params: {
          branch_id: selectedBranch,
          service_id: selectedService,
          appointment_date: selectedDate
        }
      })
      .then(res => setAvailableSlots(res.data))
      .catch(err => setError('Failed to load slots'))
      .finally(() => setLoading(false));
    }
  }, [selectedBranch, selectedService, selectedDate]);

  const handleConfirm = async () => {
    if (!selectedTime) return;
    if (loading) return;
    setLoading(true);
    setError('');
    try {
      const payload = {
        sector_id: sectorId,
        organization_id: selectedOrg,
        branch_id: selectedBranch,
        service_id: selectedService,
        appointment_date: selectedDate,
        appointment_time: selectedTime,
        notes: "Booked via User Dashboard"
      };
      const res = await api.post('/api/appointments', payload);
      
      // Step 8 fix: Create token immediately
      const tokenRes = await api.post(`/api/queue/token/${res.data.id}`);
      navigate(`/user/token/${res.data.id}`);
      
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to book appointment');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto">
      <div className="mb-8">
        <p className="text-[var(--color-primary)] font-semibold text-sm mb-2 uppercase tracking-wide">Plan Your Visit</p>
        <h1 className="text-4xl font-semibold tracking-tight text-[var(--color-text-main)] mb-2">Book an appointment.</h1>
        <p className="text-[var(--color-secondary)]">Choose an arrival window. We'll take care of your place in line.</p>
      </div>

      {error && <div className="bg-[#FFF5F5] text-[var(--color-destructive)] p-4 rounded-[10px] mb-6">{error}</div>}

      <div className="space-y-6">
        {/* Step 1: Org */}
        <div className="bg-white p-6 rounded-[18px] border border-[var(--color-border-subtle)]">
          <label className="block text-sm font-semibold mb-2">Select Organization</label>
          <select 
            value={selectedOrg} 
            onChange={e => {
              setSelectedOrg(e.target.value);
              setSelectedBranch('');
              setSelectedService('');
              setSelectedDate('');
              setSelectedTime('');
            }}
            className="w-full p-3 border border-[var(--color-border-subtle)] rounded-[10px] bg-[var(--color-canvas)]"
            disabled={organizations.length === 0}
          >
            {organizations.length === 0 ? (
              <option value="">No organizations available</option>
            ) : (
              <option value="">Choose...</option>
            )}
            {organizations.map(o => <option key={o.id} value={o.id}>{o.name}</option>)}
          </select>
        </div>

        {/* Step 2: Branch */}
        {selectedOrg && (
          <div className="bg-white p-6 rounded-[18px] border border-[var(--color-border-subtle)]">
            <label className="block text-sm font-semibold mb-2">Select Branch</label>
            <select 
              value={selectedBranch} 
              onChange={e => {
                setSelectedBranch(e.target.value);
                setSelectedService('');
                setSelectedDate('');
                setSelectedTime('');
              }}
              className="w-full p-3 border border-[var(--color-border-subtle)] rounded-[10px] bg-[var(--color-canvas)]"
              disabled={branches.length === 0}
            >
              {branches.length === 0 ? (
                <option value="">No branches available</option>
              ) : (
                <option value="">Choose...</option>
              )}
              {branches.map(b => <option key={b.id} value={b.id}>{b.address}, {b.city}</option>)}
            </select>
          </div>
        )}

        {/* Step 3: Service */}
        {selectedBranch && (
          <div className="bg-white p-6 rounded-[18px] border border-[var(--color-border-subtle)]">
            <label className="block text-sm font-semibold mb-2">Select Service</label>
            <select 
              value={selectedService} 
              onChange={e => {
                setSelectedService(e.target.value);
                setSelectedDate('');
                setSelectedTime('');
              }}
              className="w-full p-3 border border-[var(--color-border-subtle)] rounded-[10px] bg-[var(--color-canvas)]"
              disabled={services.length === 0}
            >
              {services.length === 0 ? (
                <option value="">No services available</option>
              ) : (
                <option value="">Choose...</option>
              )}
              {services.map(s => <option key={s.id} value={s.id}>{s.name} ({s.average_service_time} min)</option>)}
            </select>
          </div>
        )}

        {/* Step 4: Date & Time */}
        {selectedService && (
          <div className="bg-white p-6 rounded-[18px] border border-[var(--color-border-subtle)]">
            <h2 className="text-xl font-semibold mb-6">Choose your date & time</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div>
                <label className="block text-sm font-semibold mb-2">Date</label>
                <input 
                  type="date" 
                  min={new Date().toISOString().split('T')[0]}
                  value={selectedDate}
                  onChange={e => {
                    setSelectedDate(e.target.value);
                    setSelectedTime('');
                  }}
                  className="w-full p-3 border border-[var(--color-border-subtle)] rounded-[10px] bg-[var(--color-canvas)]"
                />
              </div>
              <div>
                <label className="block text-sm font-semibold mb-4">Available arrival windows</label>
                {loading && <p className="text-[var(--color-secondary)]">Checking slots...</p>}
                {!loading && selectedDate && availableSlots.length === 0 && (
                  <p className="text-red-500 text-sm">Fully booked. Select a different date.</p>
                )}
                {!loading && availableSlots.length > 0 && (
                  <div className="grid grid-cols-2 gap-3">
                    {availableSlots.map(time => (
                      <button
                        key={time}
                        onClick={() => setSelectedTime(time)}
                        className={`py-3 px-4 rounded-[10px] text-sm font-semibold transition-colors border ${selectedTime === time ? 'bg-[var(--color-primary)] text-white border-[var(--color-primary)]' : 'bg-white text-[var(--color-text-main)] border-[var(--color-border-subtle)] hover:border-[var(--color-primary)]'}`}
                      >
                        {time.substring(0, 5)}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Step 5: Visitor Details & Confirm */}
        {selectedTime && (
          <div className="bg-white p-6 rounded-[18px] border border-[var(--color-border-subtle)]">
            <h2 className="text-xl font-semibold mb-4">Who's visiting?</h2>
            <div className="mb-6 opacity-75 pointer-events-none">
              <input type="text" value={profile?.name || user?.name || user?.user_metadata?.full_name || 'Citizen User'} readOnly className="w-full p-3 border border-[var(--color-border-subtle)] rounded-[10px] mb-3 bg-gray-50" />
              <input type="text" value={profile?.email || user?.email || ''} readOnly className="w-full p-3 border border-[var(--color-border-subtle)] rounded-[10px] bg-gray-50" />
            </div>

            <div className="bg-[#F2F9F9] p-4 rounded-[10px] mb-6 flex items-start gap-3 border border-[#D1EBE9]">
              <svg className="w-5 h-5 text-[var(--color-primary)] mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
              <div>
                <p className="font-semibold text-sm text-[var(--color-text-main)] mb-1">Your time is an arrival window</p>
                <p className="text-sm text-[var(--color-secondary)]">You'll join the live queue for your service. The actual start time depends on queue progress.</p>
              </div>
            </div>

            <button 
              onClick={handleConfirm}
              disabled={loading}
              className="w-full bg-[var(--color-primary)] hover:bg-[#066772] text-white py-4 rounded-[10px] font-semibold flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
            >
              {loading ? 'Confirming...' : 'Confirm appointment'}
              {!loading && <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14 5l7 7m0 0l-7 7m7-7H3" /></svg>}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
