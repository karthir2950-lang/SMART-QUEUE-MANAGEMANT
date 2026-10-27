import React, { useState } from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';

export default function AdminLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, profile, logout } = useAuth();
  const { themeMode, setThemeMode } = useTheme();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);

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

  const navItems = [
    { name: 'Dashboard', path: '/admin/dashboard', icon: '📊' },
    { name: 'Organizations', path: '/admin/organizations', icon: '🏢' },
    { name: 'Branches', path: '/admin/branches', icon: '📍' },
    { name: 'Services', path: '/admin/services', icon: '🛠️' },
    { name: 'Staff Management', path: '/admin/staff', icon: '👥' },
    { name: 'Counter Management', path: '/admin/counters', icon: '🎫' },
    { name: 'Appointments', path: '/admin/appointments', icon: '📅' },
    { name: 'Tokens', path: '/admin/tokens', icon: '🎟️' },
    { name: 'Profile', path: '/admin/profile', icon: '👤' },
  ];

  const isNavActive = (item) => {
    if (location.pathname === item.path) return true;
    if (item.name === 'Tokens' && location.pathname === '/admin/queue') return true;
    return false;
  };

  const getPageTitle = () => {
    if (location.pathname === '/admin/tokens' || location.pathname === '/admin/queue') {
      return 'Admin • Tokens';
    }
    const item = navItems.find((i) => i.path === location.pathname);
    return item ? `Admin • ${item.name}` : 'Admin Portal';
  };

  const displayName = profile?.name || user?.user_metadata?.full_name || 'Admin';
  const initial = displayName.charAt(0).toUpperCase();

  return (
    <div className="min-h-screen bg-[var(--color-canvas)] text-[var(--color-text-main)] flex flex-col md:flex-row transition-colors duration-200">
      
      {/* Mobile Header Bar */}
      <div className="md:hidden flex items-center justify-between px-4 py-3 bg-[var(--color-surface)] border-b border-[var(--color-border-subtle)] sticky top-0 z-50">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-[var(--color-primary)] text-white font-bold flex items-center justify-center text-sm shadow-xs">
            A
          </div>
          <span className="font-bold text-base text-[var(--color-text-main)]">QueueLess Admin</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setThemeMode(themeMode === 'dark' ? 'light' : 'dark')}
            className="p-2 rounded-lg border border-[var(--color-border-subtle)] text-xs"
          >
            {themeMode === 'dark' ? '☀️' : '🌙'}
          </button>
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 rounded-lg border border-[var(--color-border-subtle)]"
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
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-[var(--color-primary)] text-white font-bold flex items-center justify-center text-sm">
                    A
                  </div>
                  <span className="font-bold text-base text-[var(--color-text-main)]">QueueLess Admin</span>
                </div>
                <button
                  type="button"
                  onClick={() => setMobileMenuOpen(false)}
                  className="p-1.5 rounded-lg border border-[var(--color-border-subtle)] text-sm"
                >
                  ✕
                </button>
              </div>

              <nav className="mt-4 space-y-1 overflow-y-auto max-h-[calc(100vh-220px)]">
                {navItems.map((item) => (
                  <Link
                    key={item.name}
                    to={item.path}
                    onClick={() => setMobileMenuOpen(false)}
                    className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition-colors ${
                      isNavActive(item)
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
              <div className="flex items-center gap-3 mb-3">
                <div className="w-9 h-9 rounded-full bg-[var(--color-accent-subtle)] text-[var(--color-primary)] flex items-center justify-center font-bold text-xs">
                  {initial}
                </div>
                <div className="overflow-hidden">
                  <p className="text-xs font-bold truncate text-[var(--color-text-main)]">{displayName}</p>
                  <p className="text-[10px] text-[var(--color-secondary)] truncate">{user?.email}</p>
                </div>
              </div>
              <button
                type="button"
                onClick={handleLogout}
                disabled={isLoggingOut}
                className="w-full py-2 px-3 rounded-xl border border-red-200 dark:border-red-900/60 text-red-600 dark:text-red-400 font-semibold text-xs hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors flex items-center justify-center gap-2"
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
              A
            </div>
            <div>
              <h1 className="text-lg font-bold text-[var(--color-text-main)] tracking-tight">QueueLess AI</h1>
              <p className="text-[10px] text-[var(--color-secondary)] uppercase tracking-wider font-semibold">Admin Dashboard</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 px-4 py-5 space-y-1 overflow-y-auto">
          {navItems.map((item) => (
            <Link
              key={item.name}
              to={item.path}
              className={`flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                isNavActive(item)
                  ? 'bg-[var(--color-primary)] text-white shadow-xs'
                  : 'text-[var(--color-secondary)] hover:bg-[var(--color-accent-subtle)] hover:text-[var(--color-primary)]'
              }`}
            >
              <span>{item.icon}</span>
              <span>{item.name}</span>
            </Link>
          ))}
        </nav>

        {/* Admin Card & Sign Out */}
        <div className="p-4 border-t border-[var(--color-border-subtle)] bg-[var(--color-surface)]">
          <div className="flex items-center gap-3 px-2 py-2 mb-2">
            <div className="w-9 h-9 rounded-full bg-[var(--color-accent-subtle)] text-[var(--color-primary)] flex items-center justify-center text-xs font-bold flex-shrink-0">
              {initial}
            </div>
            <div className="overflow-hidden">
              <p className="text-xs font-bold truncate text-[var(--color-text-main)]">{displayName}</p>
              <p className="text-[10px] text-[var(--color-secondary)] truncate">System Administrator</p>
            </div>
          </div>

          <button
            type="button"
            onClick={handleLogout}
            disabled={isLoggingOut}
            className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-xl text-xs font-semibold text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/30 border border-transparent hover:border-red-200 dark:hover:border-red-900/50 transition-colors"
          >
            <span>🚪</span>
            <span>{isLoggingOut ? 'Logging out...' : 'Sign Out'}</span>
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-h-screen">
        {/* Topbar */}
        <header className="bg-[var(--color-surface)] border-b border-[var(--color-border-subtle)] h-16 flex items-center justify-between px-6 sm:px-8 sticky top-0 z-30 transition-colors duration-200">
          <h2 className="text-base sm:text-lg font-bold text-[var(--color-text-main)]">
            {getPageTitle()}
          </h2>

          <div className="flex items-center gap-3">
            <Link
              to="/user/dashboard"
              className="px-3 py-1.5 rounded-xl border border-[var(--color-border-subtle)] hover:bg-[var(--color-surface-hover)] text-[var(--color-text-main)] text-xs font-semibold transition-all shadow-xs flex items-center gap-1.5 cursor-pointer"
              title="Go to User Portal"
            >
              <span>👤</span>
              <span className="hidden sm:inline">User Portal</span>
            </Link>

            <span className="hidden sm:inline text-xs font-semibold px-2.5 py-1 rounded-full bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-300">
              Admin Mode
            </span>

            {/* Global Light/Dark Mode Toggle */}
            <button
              type="button"
              onClick={() => setThemeMode(themeMode === 'dark' ? 'light' : 'dark')}
              className="p-2 rounded-xl border border-[var(--color-border-subtle)] hover:bg-[var(--color-surface-hover)] text-[var(--color-secondary)] hover:text-[var(--color-text-main)] text-xs flex items-center gap-1.5 transition-colors"
              title="Toggle theme"
            >
              <span>{themeMode === 'dark' ? '☀️' : '🌙'}</span>
              <span className="hidden sm:inline font-medium">
                {themeMode === 'dark' ? 'Light' : 'Dark'}
              </span>
            </button>

            {/* Profile Avatar */}
            <Link
              to="/admin/profile"
              className="w-8 h-8 rounded-full bg-[var(--color-accent-subtle)] text-[var(--color-primary)] flex items-center justify-center text-xs font-bold hover:scale-105 transition-transform"
              title="Admin Profile"
            >
              {initial}
            </Link>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
