import React, { useState, useEffect, useCallback } from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import api from '../services/api';
import { useRealtimeQueue } from '../hooks/useRealtimeQueue';
import LiveClockBadge from '../components/common/LiveClockBadge';

export default function UserLayout() {
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

  const [unreadNotifs, setUnreadNotifs] = useState(0);

  const fetchUnread = useCallback(async () => {
    try {
      const res = await api.get('/api/notifications', { params: { limit: 1 } });
      setUnreadNotifs(res.data.unread_count || 0);
    } catch {
      // Silent catch for background unread fetch
    }
  }, []);

  useEffect(() => {
    fetchUnread();
  }, [fetchUnread]);

  // Real-time notification updates for unread badge
  useRealtimeQueue({
    userId: user?.id,
    onNotification: useCallback((notif) => {
      if (notif && !notif.is_read) {
        setUnreadNotifs((prev) => prev + 1);
      } else {
        fetchUnread();
      }
    }, [fetchUnread]),
  });

  const isAdmin = profile?.role === 'ADMIN';
  const isStaff = profile?.role === 'STAFF';

  // Navigation items:
  const menuItems = [
    { name: 'Dashboard', path: '/user/dashboard', icon: '🏠' },
    { name: 'My Appointments', path: '/user/appointments', icon: '📅' },
    { name: 'Notifications', path: '/user/notifications', icon: '🔔', badge: unreadNotifs },
    { name: 'Settings', path: '/settings', icon: '⚙️' },
    { name: 'Profile', path: '/user/profile', icon: '👤' },
  ];

  if (isAdmin) {
    menuItems.push({ name: 'Admin Portal', path: '/admin/dashboard', icon: '⚡' });
  } else if (isStaff) {
    menuItems.push({ name: 'Staff Desk', path: '/staff/dashboard', icon: '💼' });
  }

  const getPageTitle = () => {
    if (location.pathname.startsWith('/sector')) return 'Sector Application Hub';
    if (location.pathname === '/user/appointments') return 'My Appointments';
    if (location.pathname.startsWith('/user/token')) return 'Digital Queue Token';
    if (location.pathname === '/settings') return 'Settings';
    if (location.pathname === '/user/profile') return 'My Profile';
    if (location.pathname === '/user/notifications') return 'Notifications';
    return 'Dashboard';
  };

  const displayName = profile?.name || user?.user_metadata?.full_name || user?.user_metadata?.name || 'User';
  const initial = displayName.charAt(0).toUpperCase();

  return (
    <div className="min-h-screen bg-[var(--color-canvas)] text-[var(--color-text-main)] flex flex-col md:flex-row transition-colors duration-200">
      
      {/* Mobile Header Bar */}
      <div className="md:hidden flex items-center justify-between px-4 py-3 bg-[var(--color-surface)] border-b border-[var(--color-border-subtle)] sticky top-0 z-50">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-[var(--color-primary)] text-white font-bold flex items-center justify-center text-sm shadow-xs">
            Q
          </div>
          <span className="font-bold text-base text-[var(--color-text-main)]">QueueLess AI</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setThemeMode(themeMode === 'dark' ? 'light' : 'dark')}
            className="p-2 rounded-lg border border-[var(--color-border-subtle)] text-xs"
            aria-label="Toggle theme"
          >
            {themeMode === 'dark' ? '☀️' : '🌙'}
          </button>
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 rounded-lg border border-[var(--color-border-subtle)] text-[var(--color-text-main)]"
            aria-label="Open menu"
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
              <div className="flex items-center justify-between pb-6 border-b border-[var(--color-border-subtle)]">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-[var(--color-primary)] text-white font-bold flex items-center justify-center text-sm">
                    Q
                  </div>
                  <span className="font-bold text-base text-[var(--color-text-main)]">QueueLess AI</span>
                </div>
                <button
                  type="button"
                  onClick={() => setMobileMenuOpen(false)}
                  className="p-1.5 rounded-lg border border-[var(--color-border-subtle)] text-sm"
                >
                  ✕
                </button>
              </div>

              <nav className="mt-6 space-y-1.5">
                {menuItems.map((item) => (
                  <Link
                    key={item.name}
                    to={item.path}
                    onClick={() => setMobileMenuOpen(false)}
                    className={`flex items-center justify-between px-4 py-3 rounded-xl text-sm font-semibold transition-colors ${
                      location.pathname === item.path
                        ? 'bg-[var(--color-primary)] text-white'
                        : 'text-[var(--color-secondary)] hover:bg-[var(--color-accent-subtle)] hover:text-[var(--color-primary)]'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <span>{item.icon}</span>
                      <span>{item.name}</span>
                    </div>
                    {item.badge > 0 && (
                      <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-red-500 text-white">
                        {item.badge}
                      </span>
                    )}
                  </Link>
                ))}
              </nav>
            </div>

            <div className="pt-4 border-t border-[var(--color-border-subtle)]">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-full bg-[var(--color-accent-subtle)] text-[var(--color-primary)] flex items-center justify-center font-bold text-sm">
                  {initial}
                </div>
                <div className="overflow-hidden">
                  <p className="text-sm font-bold truncate text-[var(--color-text-main)]">{displayName}</p>
                  <p className="text-xs text-[var(--color-secondary)] truncate">{user?.email}</p>
                </div>
              </div>

              <button
                type="button"
                onClick={handleLogout}
                disabled={isLoggingOut}
                className="w-full py-2.5 px-4 rounded-xl border border-red-200 dark:border-red-900/60 text-red-600 dark:text-red-400 font-semibold text-xs hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors flex items-center justify-center gap-2 cursor-pointer"
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
              Q
            </div>
            <div>
              <h1 className="text-lg font-bold text-[var(--color-text-main)] tracking-tight">QueueLess AI</h1>
              <p className="text-[10px] text-[var(--color-secondary)] uppercase tracking-wider font-semibold">User Portal</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 px-4 py-6 space-y-1.5 overflow-y-auto">
          {menuItems.map((item) => (
            <Link
              key={item.name}
              to={item.path}
              className={`flex items-center justify-between px-4 py-3 rounded-xl text-sm font-semibold transition-all ${
                location.pathname === item.path
                  ? 'bg-[var(--color-primary)] text-white shadow-xs'
                  : 'text-[var(--color-secondary)] hover:bg-[var(--color-accent-subtle)] hover:text-[var(--color-primary)]'
              }`}
            >
              <div className="flex items-center gap-3">
                <span>{item.icon}</span>
                <span>{item.name}</span>
              </div>
              {item.badge > 0 && (
                <span className={`px-2 py-0.5 rounded-full text-[11px] font-bold ${
                  location.pathname === item.path ? 'bg-white text-[var(--color-primary)]' : 'bg-[var(--color-primary)] text-white'
                }`}>
                  {item.badge}
                </span>
              )}
            </Link>
          ))}
        </nav>

        {/* User Card & Logout in Desktop Sidebar */}
        <div className="p-4 border-t border-[var(--color-border-subtle)] bg-[var(--color-surface)]">
          <div className="flex items-center gap-3 px-2 py-2 mb-3">
            <div className="w-10 h-10 rounded-full bg-[var(--color-accent-subtle)] text-[var(--color-primary)] flex items-center justify-center text-sm font-bold flex-shrink-0">
              {initial}
            </div>
            <div className="overflow-hidden">
              <p className="text-sm font-bold truncate text-[var(--color-text-main)]">{displayName}</p>
              <p className="text-xs text-[var(--color-secondary)] truncate">{user?.email}</p>
            </div>
          </div>

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
        {/* Topbar */}
        <header className="bg-[var(--color-surface)] border-b border-[var(--color-border-subtle)] h-16 flex items-center justify-between px-6 sm:px-8 sticky top-0 z-30 transition-colors duration-200">
          <div className="flex items-center gap-4">
            <h2 className="text-base sm:text-lg font-bold text-[var(--color-text-main)]">
              {getPageTitle()}
            </h2>
            <div className="hidden lg:block">
              <LiveClockBadge compact={true} />
            </div>
          </div>

          <div className="flex items-center gap-3">
            {isAdmin && (
              <Link
                to="/admin/dashboard"
                className="px-3 py-1.5 rounded-xl bg-purple-600 hover:bg-purple-700 text-white text-xs font-bold transition-all shadow-xs flex items-center gap-1.5 cursor-pointer"
                title="Go to Admin Portal"
              >
                <span>⚡</span>
                <span className="hidden sm:inline">Admin Dashboard</span>
              </Link>
            )}

            {/* Live Notifications Bell */}
            <Link
              to="/user/notifications"
              className="p-2 rounded-xl border border-[var(--color-border-subtle)] hover:bg-[var(--color-surface-hover)] text-[var(--color-secondary)] hover:text-[var(--color-text-main)] text-sm flex items-center justify-center relative transition-colors cursor-pointer"
              title="Notifications"
            >
              <span>🔔</span>
              {unreadNotifs > 0 && (
                <span className="absolute -top-1.5 -right-1.5 px-1.5 py-0.2 rounded-full text-[10px] font-extrabold bg-red-500 text-white min-w-[18px] text-center shadow-xs animate-bounce">
                  {unreadNotifs}
                </span>
              )}
            </Link>

            {/* Global Light/Dark Mode Toggle */}
            <button
              type="button"
              onClick={() => setThemeMode(themeMode === 'dark' ? 'light' : 'dark')}
              className="p-2 rounded-xl border border-[var(--color-border-subtle)] hover:bg-[var(--color-surface-hover)] text-[var(--color-secondary)] hover:text-[var(--color-text-main)] text-xs flex items-center gap-1.5 transition-colors cursor-pointer"
              title="Toggle theme"
            >
              <span>{themeMode === 'dark' ? '☀️' : '🌙'}</span>
              <span className="hidden sm:inline font-medium">
                {themeMode === 'dark' ? 'Light' : 'Dark'}
              </span>
            </button>

            {/* Profile Link Icon */}
            <Link
              to="/user/profile"
              className="w-8 h-8 rounded-full bg-[var(--color-accent-subtle)] text-[var(--color-primary)] flex items-center justify-center text-xs font-bold hover:scale-105 transition-transform"
              title="Profile"
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
