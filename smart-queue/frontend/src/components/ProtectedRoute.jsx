import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function ProtectedRoute({ children, allowedRoles }) {
  const { user, profile, loading } = useAuth();
  const location = useLocation();

  if (loading || (user && !profile)) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--color-canvas)] text-[var(--color-secondary)]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-3 border-[var(--color-primary)] border-t-transparent rounded-full animate-spin"></div>
          <span className="text-sm font-medium">Verifying authorization...</span>
        </div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (allowedRoles && allowedRoles.length > 0) {
    const role = profile?.role || 'USER';
    if (!allowedRoles.includes(role)) {
      if (role === 'ADMIN') return <Navigate to="/admin/dashboard" replace />;
      if (role === 'STAFF') return <Navigate to="/staff/dashboard" replace />;
      return <Navigate to="/user/dashboard" replace />;
    }
  }

  return children;
}
