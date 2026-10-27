import React from 'react';
import { HashRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import UserLayout from './layouts/UserLayout';
import AdminLayout from './layouts/AdminLayout';
import StaffLayout from './layouts/StaffLayout';
import ProtectedRoute from './components/ProtectedRoute';
import { useAuth } from './context/AuthContext';

// Lazy-loaded User pages
const Login = React.lazy(() => import('./pages/Login'));
const AuthCallback = React.lazy(() => import('./pages/AuthCallback'));
const Dashboard = React.lazy(() => import('./pages/Dashboard'));
const SectorExplorer = React.lazy(() => import('./pages/user/SectorExplorer'));
const Booking = React.lazy(() => import('./pages/user/Booking'));
const TokenPage = React.lazy(() => import('./pages/user/TokenPage'));
const MyAppointments = React.lazy(() => import('./pages/user/MyAppointments'));
const Settings = React.lazy(() => import('./pages/user/Settings'));
const Profile = React.lazy(() => import('./pages/user/Profile'));
const Notifications = React.lazy(() => import('./pages/user/Notifications'));
const VerifyToken = React.lazy(() => import('./pages/VerifyToken'));

// Lazy-loaded Admin pages (STEP 7)
const AdminDashboard = React.lazy(() => import('./pages/admin/AdminDashboard'));
const AdminOrganizations = React.lazy(() => import('./pages/admin/AdminOrganizations'));
const AdminBranches = React.lazy(() => import('./pages/admin/AdminBranches'));
const AdminServices = React.lazy(() => import('./pages/admin/AdminServices'));
const AdminStaff = React.lazy(() => import('./pages/admin/AdminStaff'));
const AdminCounters = React.lazy(() => import('./pages/admin/AdminCounters'));
const AdminAppointments = React.lazy(() => import('./pages/admin/AdminAppointments'));
const AdminTokens = React.lazy(() => import('./pages/admin/AdminTokens'));

// Lazy-loaded Staff pages (STEP 7)
const StaffDashboard = React.lazy(() => import('./pages/staff/StaffDashboard'));
const StaffAppointments = React.lazy(() => import('./pages/staff/StaffAppointments'));
const StaffTokens = React.lazy(() => import('./pages/staff/StaffTokens'));

const LoadingFallback = () => (
  <div className="min-h-screen flex items-center justify-center bg-[var(--color-canvas)] text-[var(--color-secondary)]">
    <div className="flex flex-col items-center gap-3">
      <div className="w-8 h-8 border-3 border-[var(--color-primary)] border-t-transparent rounded-full animate-spin"></div>
      <span className="text-sm font-medium">Loading QueueLess AI...</span>
    </div>
  </div>
);

function RoleBasedDashboardRedirect() {
  const { profile, session, user } = useAuth();
  const provider = session?.user?.app_metadata?.provider || user?.app_metadata?.provider;
  if (provider === 'google') return <Navigate to="/user/dashboard" replace />;
  const role = profile?.role || 'USER';
  if (role === 'ADMIN') return <Navigate to="/admin/dashboard" replace />;
  if (role === 'STAFF') return <Navigate to="/staff/dashboard" replace />;
  return <Navigate to="/user/dashboard" replace />;
}

function App() {
  return (
    <Router basename={import.meta.env.BASE_URL}>
      <Routes>
        {/* Entry page: ALWAYS /login */}
        <Route path="/" element={<Navigate to="/login" replace />} />

        {/* Authentication: LOGIN & SIGNUP */}
        <Route
          path="/login"
          element={
            <React.Suspense fallback={<LoadingFallback />}>
              <Login />
            </React.Suspense>
          }
        />
        <Route
          path="/auth/callback"
          element={
            <React.Suspense fallback={<LoadingFallback />}>
              <AuthCallback />
            </React.Suspense>
          }
        />
        <Route path="/signup" element={<Navigate to="/login?mode=signup" replace />} />

        {/* Public Pass Verification (QR Scan) */}
        <Route
          path="/verify/token/:secureToken"
          element={
            <React.Suspense fallback={<LoadingFallback />}>
              <VerifyToken />
            </React.Suspense>
          }
        />

        {/* Standalone Sector Routes (Protected User & Permitted Roles) */}
        <Route
          path="/sector"
          element={
            <ProtectedRoute allowedRoles={['USER', 'ADMIN', 'STAFF']}>
              <UserLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/user/dashboard" replace />} />
          <Route
            path=":sectorSlug"
            element={
              <React.Suspense fallback={<LoadingFallback />}>
                <SectorExplorer />
              </React.Suspense>
            }
          />
          <Route
            path=":sectorSlug/organization/:organizationId"
            element={
              <React.Suspense fallback={<LoadingFallback />}>
                <SectorExplorer />
              </React.Suspense>
            }
          />
          <Route
            path=":sectorSlug/branch/:branchId"
            element={
              <React.Suspense fallback={<LoadingFallback />}>
                <SectorExplorer />
              </React.Suspense>
            }
          />
          <Route
            path=":sectorSlug/service/:serviceId"
            element={
              <React.Suspense fallback={<LoadingFallback />}>
                <SectorExplorer />
              </React.Suspense>
            }
          />
        </Route>

        {/* Dedicated Settings Page (Protected User & Permitted Roles) */}
        <Route
          path="/settings"
          element={
            <ProtectedRoute allowedRoles={['USER', 'ADMIN', 'STAFF']}>
              <UserLayout />
            </ProtectedRoute>
          }
        >
          <Route
            index
            element={
              <React.Suspense fallback={<LoadingFallback />}>
                <Settings />
              </React.Suspense>
            }
          />
        </Route>

        {/* Protected User Dashboard and Features */}
        <Route
          path="/user"
          element={
            <ProtectedRoute allowedRoles={['USER', 'ADMIN', 'STAFF']}>
              <UserLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="dashboard" replace />} />
          <Route
            path="dashboard"
            element={
              <React.Suspense fallback={<LoadingFallback />}>
                <Dashboard />
              </React.Suspense>
            }
          />
          <Route
            path="book/:sectorId"
            element={
              <React.Suspense fallback={<LoadingFallback />}>
                <Booking />
              </React.Suspense>
            }
          />
          <Route
            path="token/:appointmentId"
            element={
              <React.Suspense fallback={<LoadingFallback />}>
                <TokenPage />
              </React.Suspense>
            }
          />
          <Route
            path="appointments"
            element={
              <React.Suspense fallback={<LoadingFallback />}>
                <MyAppointments />
              </React.Suspense>
            }
          />
          <Route
            path="profile"
            element={
              <React.Suspense fallback={<LoadingFallback />}>
                <Profile />
              </React.Suspense>
            }
          />
          <Route
            path="notifications"
            element={
              <React.Suspense fallback={<LoadingFallback />}>
                <Notifications />
              </React.Suspense>
            }
          />
        </Route>

        {/* General /dashboard role-aware redirect */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <RoleBasedDashboardRedirect />
            </ProtectedRoute>
          }
        />

        {/* Protected /booking/* and /book/* aliases */}
        <Route
          path="/booking/*"
          element={
            <ProtectedRoute>
              <Navigate to="/user/dashboard" replace />
            </ProtectedRoute>
          }
        />
        <Route
          path="/book/*"
          element={
            <ProtectedRoute>
              <Navigate to="/user/dashboard" replace />
            </ProtectedRoute>
          }
        />

        {/* Protected Admin Routes (STEP 7) */}
        <Route
          path="/admin"
          element={
            <ProtectedRoute allowedRoles={['ADMIN']}>
              <AdminLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="dashboard" replace />} />
          <Route
            path="dashboard"
            element={
              <React.Suspense fallback={<LoadingFallback />}>
                <AdminDashboard />
              </React.Suspense>
            }
          />
          <Route
            path="organizations"
            element={
              <React.Suspense fallback={<LoadingFallback />}>
                <AdminOrganizations />
              </React.Suspense>
            }
          />
          <Route
            path="branches"
            element={
              <React.Suspense fallback={<LoadingFallback />}>
                <AdminBranches />
              </React.Suspense>
            }
          />
          <Route
            path="services"
            element={
              <React.Suspense fallback={<LoadingFallback />}>
                <AdminServices />
              </React.Suspense>
            }
          />
          <Route
            path="staff"
            element={
              <React.Suspense fallback={<LoadingFallback />}>
                <AdminStaff />
              </React.Suspense>
            }
          />
          <Route
            path="counters"
            element={
              <React.Suspense fallback={<LoadingFallback />}>
                <AdminCounters />
              </React.Suspense>
            }
          />
          <Route
            path="appointments"
            element={
              <React.Suspense fallback={<LoadingFallback />}>
                <AdminAppointments />
              </React.Suspense>
            }
          />
          <Route
            path="tokens"
            element={
              <React.Suspense fallback={<LoadingFallback />}>
                <AdminTokens />
              </React.Suspense>
            }
          />
          <Route path="queue" element={<Navigate to="tokens" replace />} />
          <Route
            path="profile"
            element={
              <React.Suspense fallback={<LoadingFallback />}>
                <Profile />
              </React.Suspense>
            }
          />
        </Route>

        {/* Protected Staff Routes (Private Staff Portal) */}
        <Route
          path="/staff"
          element={
            <ProtectedRoute allowedRoles={['STAFF']}>
              <StaffLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="dashboard" replace />} />
          <Route
            path="dashboard"
            element={
              <React.Suspense fallback={<LoadingFallback />}>
                <StaffDashboard />
              </React.Suspense>
            }
          />
          <Route
            path="appointments"
            element={
              <React.Suspense fallback={<LoadingFallback />}>
                <StaffAppointments />
              </React.Suspense>
            }
          />
          <Route
            path="tokens"
            element={
              <React.Suspense fallback={<LoadingFallback />}>
                <StaffTokens />
              </React.Suspense>
            }
          />
          <Route
            path="profile"
            element={
              <React.Suspense fallback={<LoadingFallback />}>
                <Profile />
              </React.Suspense>
            }
          />
        </Route>

        {/* Catch-all unknown paths */}
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
