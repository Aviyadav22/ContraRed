import React, { Suspense, useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { isAuthenticated, isAdmin, validateSession, clearAuth } from '@/api/client';

const Landing = React.lazy(() => import('@/pages/Landing'));
const Login = React.lazy(() => import('@/pages/Login'));
const Register = React.lazy(() => import('@/pages/Register'));
const Dashboard = React.lazy(() => import('@/pages/Dashboard'));
const Playbooks = React.lazy(() => import('@/pages/Playbooks'));
const PlaybookEditor = React.lazy(() => import('@/pages/PlaybookEditor'));
const Billing = React.lazy(() => import('@/pages/Billing'));
const AuditLogs = React.lazy(() => import('@/pages/AuditLogs'));
const Team = React.lazy(() => import('@/pages/Team'));
const NotFound = React.lazy(() => import('@/pages/NotFound'));
const ClauseLibrary = React.lazy(() => import('@/pages/ClauseLibrary'));
const Templates = React.lazy(() => import('@/pages/Templates'));
const Analytics = React.lazy(() => import('@/pages/Analytics'));
const Compare = React.lazy(() => import('@/pages/Compare'));
const BatchUpload = React.lazy(() => import('@/pages/BatchUpload'));
const Executive = React.lazy(() => import('@/pages/Executive'));
const Reports = React.lazy(() => import('@/pages/Reports'));
const Marketplace = React.lazy(() => import('@/pages/Marketplace'));
const ForgotPassword = React.lazy(() => import('@/pages/ForgotPassword'));


const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30000, // 30 seconds
      refetchOnWindowFocus: false,
    },
  },
});

// Protected route wrapper with server-side session validation
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const [validated, setValidated] = useState<boolean | null>(null);

  useEffect(() => {
    // Quick client check first
    if (!isAuthenticated()) {
      setValidated(false);
      return;
    }
    // Server-side validation
    validateSession()
      .then((user) => setValidated(!!user))
      .catch(() => {
        clearAuth();
        setValidated(false);
      });
  }, []);

  if (validated === null) {
    return <div className="flex items-center justify-center h-screen">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
    </div>;
  }
  if (!validated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

// Admin-only route wrapper with server-side session + role validation
function AdminRoute({ children }: { children: React.ReactNode }) {
  const [validated, setValidated] = useState<'loading' | 'admin' | 'user' | 'unauthenticated'>('loading');

  useEffect(() => {
    if (!isAuthenticated()) {
      setValidated('unauthenticated');
      return;
    }
    validateSession()
      .then((user) => {
        if (user && (user.role === 'admin' || user.role === 'super_admin')) {
          setValidated('admin');
        } else if (user) {
          setValidated('user');
        } else {
          clearAuth();
          setValidated('unauthenticated');
        }
      })
      .catch(() => {
        clearAuth();
        setValidated('unauthenticated');
      });
  }, []);

  if (validated === 'loading') {
    return <div className="flex items-center justify-center h-screen">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
    </div>;
  }
  if (validated === 'unauthenticated') return <Navigate to="/login" replace />;
  if (validated === 'user') return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Suspense fallback={<div className="flex flex-col items-center justify-center min-h-screen" style={{ backgroundColor: '#FAFAF9' }}><div className="text-2xl font-bold mb-4" style={{ color: '#C0392B' }}>ContraRed</div><div className="animate-spin rounded-full h-8 w-8 border-2 border-slate-300" style={{ borderTopColor: '#C0392B' }}></div></div>}>
          <Routes>
            {/* Public routes */}
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />

            {/* Protected routes - all authenticated users */}
            <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
            <Route path="/playbooks" element={<ProtectedRoute><Playbooks /></ProtectedRoute>} />
            <Route path="/clause-library" element={<ProtectedRoute><ClauseLibrary /></ProtectedRoute>} />
            <Route path="/templates" element={<ProtectedRoute><Templates /></ProtectedRoute>} />
            <Route path="/compare" element={<ProtectedRoute><Compare /></ProtectedRoute>} />
            <Route path="/batch-upload" element={<ProtectedRoute><BatchUpload /></ProtectedRoute>} />
            <Route path="/audit-logs" element={<ProtectedRoute><AuditLogs /></ProtectedRoute>} />
            <Route path="/marketplace" element={<ProtectedRoute><Marketplace /></ProtectedRoute>} />

            {/* Admin-only routes */}
            <Route path="/playbooks/:id" element={<AdminRoute><PlaybookEditor /></AdminRoute>} />
            <Route path="/analytics" element={<AdminRoute><Analytics /></AdminRoute>} />
            <Route path="/billing" element={<AdminRoute><Billing /></AdminRoute>} />
            <Route path="/team" element={<AdminRoute><Team /></AdminRoute>} />
            <Route path="/executive" element={<AdminRoute><Executive /></AdminRoute>} />
            <Route path="/reports" element={<AdminRoute><Reports /></AdminRoute>} />

            {/* Catch-all 404 */}
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
