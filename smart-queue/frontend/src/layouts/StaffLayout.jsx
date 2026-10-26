import React, { useState, useEffect } from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import api from '../services/api';

export default function StaffLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, profile, logout } = useAuth();
  const { themeMode, setThemeMode } = useTheme();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [assignedCounter, setAssignedCounter] = useState(null);

  const handleLogout = async () => {
    if (isLoggingOut) return;
    setIsLoggingOut(true);
    try {
      await logout();
      navigate('/login', { replace: true });
    } catch (err) {
      console.error('Logout error:', err);
    } finally {
      setIsLoggingOut(false);
    }
  };

  useEffect(() => {
    let active = true;
    api.get('/api/staff/dashboard/summary')
      .then((res) => {
        if (active && res.data?.assigned_counter) {
          setAssignedCounter(res.data.assigned_counter);
        }
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  // Strictly Staff-facing navigation items:
  // - Staff Dashboard
  // - Appointments
  // - Queue/Tokens
  // - Assigned Counter (displayed as status badge)
  // - Profile
  // - Logout
  const navItems = [
    { name: 'Staff Dashboard', path: '/staff/dashboard', icon: '📋' },
    { name: 'Appointments', path: '/staff/appointments', icon: '📅' },
    { name: 'Queue / Tokens', path: '/staff/tokens', icon: '🎟️' },
    { name: 'Profile', path: '/staff/profile', icon: '👤' },
  ];

  const displayName = profile?.name || user?.user_metadata?.full_name || 'Staff Member';
  const initial = displayName.charAt(0).toUpperCase();

  return (
    <div className="min-h-screen bg-[var(--color-canvas)] text-[var(--color-text-main)] flex flex-col md:flex-row transition-colors duration-200">
      
      {/* Mobile Top Bar */}
      <div className="md:hidden flex items-center justify-between px-4 py-3 bg-[var(--color-surface)] border-b border-[var(--color-border-subtle)] sticky top-0 z-50">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-[var(--color-primary)] text-white font-bold flex items-center justify-center text-sm shadow-xs">
            S
          </div>
          <span className="font-bold text-base text-[var(--color-text-main)]">Staff Portal</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setThemeMode(themeMode === 'dark' ? 'light' : 'dark')}
            className="p-2 rounded-lg border border-[var(--color-border-subtle)] text-xs cursor-pointer"
          >
            {themeMode === 'dark' ? '☀️' : '🌙'}
          </button>
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 rounded-lg border border-[var(--color-border-subtle)] cursor-pointer"
          >
            {mobileMenuOpen ? '✕' : '☰'}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden fixed inset-0 z-40 bg-black/50 backdrop-blur-xs flex flex-col">
          <div className="w-4/5 max-w-xs h-full bg-[var(--color-surface)] p-6 flex flex-col justify-between shadow-xl">
            <div>
              <div className="flex items-center justify-between pb-4 border-b border-[var(--color-border-subtle)]">
                <span className="font-bold text-base text-[var(--color-text-main)]">Staff Portal</span>
                <button
                  type="button"
                  onClick={() => setMobileMenuOpen(false)}
                  className="p-1.5 rounded-lg border border-[var(--color-border-subtle)] text-sm cursor-pointer"
                >
                  ✕
                </button>
              </div>

              {assignedCounter && (
                <div className="mt-3 p-2.5 rounded-xl bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-900/60 text-xs">
                  <span className="text-[10px] uppercase font-bold text-blue-700 dark:text-blue-300 block">Assigned Station</span>
                  <span className="font-bold text-blue-900 dark:text-blue-200">{assignedCounter}</span>
                </div>
              )}

              <nav className="mt-4 space-y-1">
                {navItems.map((item) => (
                  <Link
                    key={item.name}
                    to={item.path}
                    onClick={() => setMobileMenuOpen(false)}
                    className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition-colors ${
                      location.pathname === item.path
                        ? 'bg-[var(--color-primary)] text-white'
                        : 'text-[var(--color-secondary)] hover:bg-[var(--color-accent-subtle)] hover:text-[var(--color-primary)]'
                    }`}
                  >
                    <span>{item.icon}</span>
                    <span>{item.name}</span>
                  </Link>
                ))}
              </nav>
            </div>

            <div className="pt-4 border-t border-[var(--color-border-subtle)]">
              <button
                type="button"
                onClick={handleLogout}
                disabled={isLoggingOut}
                className="w-full py-2 px-3 rounded-xl border border-red-200 dark:border-red-900/60 text-red-600 dark:text-red-400 font-semibold text-xs hover:bg-red-50 dark:hover:bg-red-950/30 flex items-center justify-center gap-2 cursor-pointer"
              >
                <span>🚪</span>
                <span>{isLoggingOut ? 'Logging out...' : 'Sign Out'}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Desktop Sidebar */}
      <aside className="hidden md:flex w-64 bg-[var(--color-surface)] border-r border-[var(--color-border-subtle)] flex-col h-screen sticky top-0 transition-colors duration-200">
        <div className="p-6 border-b border-[var(--color-border-subtle)]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[var(--color-primary)] flex items-center justify-center text-white font-bold text-lg shadow-xs">
              S
            </div>
            <div>
              <h1 className="text-lg font-bold text-[var(--color-text-main)] tracking-tight">QueueLess AI</h1>
              <p className="text-[10px] text-[var(--color-secondary)] uppercase tracking-wider font-semibold">Staff Station</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 px-4 py-5 space-y-1 overflow-y-auto">
          {navItems.map((item) => (
            <Link
              key={item.name}
              to={item.path}
              className={`flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                location.pathname === item.path
                  ? 'bg-[var(--color-primary)] text-white shadow-xs'
                  : 'text-[var(--color-secondary)] hover:bg-[var(--color-accent-subtle)] hover:text-[var(--color-primary)]'
              }`}
            >
              <span>{item.icon}</span>
              <span>{item.name}</span>
            </Link>
          ))}
        </nav>

        {/* Staff Card, Assigned Station & Logout */}
        <div className="p-4 border-t border-[var(--color-border-subtle)] bg-[var(--color-surface)]">
          <div className="flex items-center gap-3 px-2 py-2 mb-2">
            <div className="w-9 h-9 rounded-full bg-[var(--color-accent-subtle)] text-[var(--color-primary)] flex items-center justify-center text-xs font-bold flex-shrink-0">
              {initial}
            </div>
            <div className="overflow-hidden">
              <p className="text-xs font-bold truncate text-[var(--color-text-main)]">{displayName}</p>
              <p className="text-[10px] text-[var(--color-secondary)] truncate">Branch Operations</p>
            </div>
          </div>

          {assignedCounter && (
            <div className="mb-3 px-3 py-2 rounded-xl bg-[var(--color-canvas)] border border-[var(--color-border-subtle)] flex items-center justify-between text-xs">
              <span className="text-[10px] uppercase font-bold text-[var(--color-secondary)]">Station:</span>
              <span className="font-bold text-[var(--color-primary)] truncate ml-1">{assignedCounter}</span>
            </div>
          )}

          <button
            type="button"
            onClick={handleLogout}
            disabled={isLoggingOut}
            className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-xl text-xs font-semibold text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/30 border border-transparent hover:border-red-200 dark:hover:border-red-900/50 transition-colors cursor-pointer"
          >
            <span>🚪</span>
            <span>{isLoggingOut ? 'Logging out...' : 'Sign Out'}</span>
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-h-screen">
        <header className="bg-[var(--color-surface)] border-b border-[var(--color-border-subtle)] h-16 flex items-center justify-between px-6 sm:px-8 sticky top-0 z-30 transition-colors duration-200">
          <h2 className="text-base sm:text-lg font-bold text-[var(--color-text-main)]">
            Staff Portal
          </h2>

          <div className="flex items-center gap-3">
            {assignedCounter && (
              <span className="hidden sm:inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1 rounded-full bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300 border border-blue-200 dark:border-blue-900">
                <span>🎫</span>
                <span>{assignedCounter}</span>
              </span>
            )}

            <button
              type="button"
              onClick={() => setThemeMode(themeMode === 'dark' ? 'light' : 'dark')}
              className="p-2 rounded-xl border border-[var(--color-border-subtle)] hover:bg-[var(--color-surface-hover)] text-[var(--color-secondary)] hover:text-[var(--color-text-main)] text-xs flex items-center gap-1.5 transition-colors cursor-pointer"
              title="Toggle theme"
            >
              <span>{themeMode === 'dark' ? '☀️' : '🌙'}</span>
            </button>

            {/* Profile Avatar linking to /staff/profile */}
            <Link
              to="/staff/profile"
              className="w-8 h-8 rounded-full bg-[var(--color-accent-subtle)] text-[var(--color-primary)] flex items-center justify-center text-xs font-bold hover:scale-105 transition-transform"
              title="Staff Profile"
            >
              {initial}
            </Link>
          </div>
        </header>

        <main className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
