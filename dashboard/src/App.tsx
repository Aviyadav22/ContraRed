import React, { Suspense, useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { isAuthenticated, validateSession, clearAuth } from '@/api/client';
import ErrorBoundary from '@/components/ErrorBoundary';
import { ThemeProvider } from '@/contexts/ThemeContext';
import { ToastProvider } from '@/contexts/ToastContext';
import { ToastContainer } from '@/components/ui/Toast';
import { ConsentBanner } from '@/components/ConsentBanner';
import { ConsentPromptModal } from '@/components/ConsentPromptModal';

const Landing = React.lazy(() => import('@/pages/Landing'));
const Login = React.lazy(() => import('@/pages/Login'));
const Register = React.lazy(() => import('@/pages/Register'));
const Dashboard = React.lazy(() => import('@/pages/Dashboard'));
const Playbooks = React.lazy(() => import('@/pages/Playbooks'));
const PlaybookEditor = React.lazy(() => import('@/pages/playbook-editor'));
const Billing = React.lazy(() => import('@/pages/Billing'));
const AuditLogs = React.lazy(() => import('@/pages/AuditLogs'));
const Team = React.lazy(() => import('@/pages/Team'));
const NotFound = React.lazy(() => import('@/pages/NotFound'));
const ClauseLibrary = React.lazy(() => import('@/pages/ClauseLibrary'));
const Analytics = React.lazy(() => import('@/pages/Analytics'));
const Compare = React.lazy(() => import('@/pages/Compare'));
const BatchUpload = React.lazy(() => import('@/pages/BatchUpload'));
const Executive = React.lazy(() => import('@/pages/Executive'));
const Reports = React.lazy(() => import('@/pages/Reports'));
const Marketplace = React.lazy(() => import('@/pages/Marketplace'));
const ForgotPassword = React.lazy(() => import('@/pages/ForgotPassword'));
const Drafting = React.lazy(() => import('@/pages/drafting'));
const ConsentPreferences = React.lazy(() => import('@/pages/ConsentPreferences'));
const DataRights = React.lazy(() => import('@/pages/DataRights'));
const ComplianceDashboard = React.lazy(() => import('@/pages/ComplianceDashboard'));
const DPDPCommandCenter = React.lazy(() => import('@/pages/DPDPCommandCenter'));
const Redline = React.lazy(() => import('@/pages/redline'));


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
    return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', backgroundColor: 'var(--bg-app)' }}>
      <div style={{ width: 32, height: 32, border: '2px solid var(--border)', borderTopColor: 'var(--accent)', borderRadius: '50%', animation: 'spin 0.7s linear infinite' }} />
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
    return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', backgroundColor: 'var(--bg-app)' }}>
      <div style={{ width: 32, height: 32, border: '2px solid var(--border)', borderTopColor: 'var(--accent)', borderRadius: '50%', animation: 'spin 0.7s linear infinite' }} />
    </div>;
  }
  if (validated === 'unauthenticated') return <Navigate to="/login" replace />;
  if (validated === 'user') return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <ThemeProvider>
    <ToastProvider>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Suspense fallback={<div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', backgroundColor: 'var(--bg-app)', gap: 16 }}><div style={{ fontSize: 24, fontWeight: 700, color: 'var(--accent)' }}>ContraRed</div><div style={{ width: 32, height: 32, border: '2px solid var(--border)', borderTopColor: 'var(--accent)', borderRadius: '50%', animation: 'spin 0.7s linear infinite' }} /></div>}>
          <ErrorBoundary>
          <Routes>
            {/* Public routes */}
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />

            {/* Protected routes - all authenticated users */}
            <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
            <Route path="/drafting" element={<ProtectedRoute><Drafting /></ProtectedRoute>} />
            <Route path="/playbooks" element={<ProtectedRoute><Playbooks /></ProtectedRoute>} />
            <Route path="/clause-library" element={<ProtectedRoute><ClauseLibrary /></ProtectedRoute>} />
            <Route path="/compare" element={<ProtectedRoute><Compare /></ProtectedRoute>} />
            <Route path="/redline" element={<ProtectedRoute><Redline /></ProtectedRoute>} />
            <Route path="/batch-upload" element={<ProtectedRoute><BatchUpload /></ProtectedRoute>} />
            <Route path="/audit-logs" element={<ProtectedRoute><AuditLogs /></ProtectedRoute>} />
            <Route path="/settings/privacy" element={<ProtectedRoute><ConsentPreferences /></ProtectedRoute>} />
            <Route path="/settings/data-rights" element={<ProtectedRoute><DataRights /></ProtectedRoute>} />
            <Route path="/marketplace" element={<ProtectedRoute><Marketplace /></ProtectedRoute>} />

            {/* Admin-only routes */}
            {/* Playbook editor is accessible to any authenticated user — the backend
                enforces ownership via _get_playbook_or_403 for every mutation, and the
                editor's own UI shows view-only state for non-owned playbooks. */}
            <Route path="/playbooks/:id" element={<ProtectedRoute><PlaybookEditor /></ProtectedRoute>} />
            <Route path="/analytics" element={<AdminRoute><Analytics /></AdminRoute>} />
            <Route path="/billing" element={<AdminRoute><Billing /></AdminRoute>} />
            <Route path="/team" element={<AdminRoute><Team /></AdminRoute>} />
            <Route path="/executive" element={<AdminRoute><Executive /></AdminRoute>} />
            <Route path="/reports" element={<AdminRoute><Reports /></AdminRoute>} />
            <Route path="/compliance" element={<AdminRoute><ComplianceDashboard /></AdminRoute>} />
            <Route path="/dpdp" element={<ProtectedRoute><DPDPCommandCenter /></ProtectedRoute>} />

            {/* Catch-all 404 */}
            <Route path="*" element={<NotFound />} />
          </Routes>
          {/* DPDP consent banner — shown when AI consent not yet granted */}
          {isAuthenticated() && <ConsentBanner />}
          <ConsentPromptModal />
          </ErrorBoundary>
        </Suspense>
      </BrowserRouter>
    </QueryClientProvider>
    <ToastContainer />
    </ToastProvider>
    </ThemeProvider>
  );
}
