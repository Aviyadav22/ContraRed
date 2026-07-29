import React, { Suspense, useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { isAuthenticated, validateSession, clearAuth, getStoredUser, type User } from '@/api/client';
import ErrorBoundary from '@/components/ErrorBoundary';
import { ThemeProvider } from '@/contexts/ThemeContext';
import { ToastProvider } from '@/contexts/ToastContext';
import { ToastContainer } from '@/components/ui/Toast';
import { ConsentBanner } from '@/components/ConsentBanner';
import { ConsentPromptModal } from '@/components/ConsentPromptModal';

const pageImports = {
  landing: () => import('@/pages/Landing'),
  login: () => import('@/pages/Login'),
  register: () => import('@/pages/Register'),
  dashboard: () => import('@/pages/Dashboard'),
  playbooks: () => import('@/pages/Playbooks'),
  playbookEditor: () => import('@/pages/playbook-editor'),
  billing: () => import('@/pages/Billing'),
  auditLogs: () => import('@/pages/AuditLogs'),
  team: () => import('@/pages/Team'),
  notFound: () => import('@/pages/NotFound'),
  clauseLibrary: () => import('@/pages/ClauseLibrary'),
  analytics: () => import('@/pages/Analytics'),
  compare: () => import('@/pages/Compare'),
  batchUpload: () => import('@/pages/BatchUpload'),
  executive: () => import('@/pages/Executive'),
  reports: () => import('@/pages/Reports'),
  marketplace: () => import('@/pages/Marketplace'),
  forgotPassword: () => import('@/pages/ForgotPassword'),
  drafting: () => import('@/pages/drafting'),
  consentPreferences: () => import('@/pages/ConsentPreferences'),
  dataRights: () => import('@/pages/DataRights'),
  dpdpCommandCenter: () => import('@/pages/DPDPCommandCenter'),
  redline: () => import('@/pages/redline'),
};

const Landing = React.lazy(pageImports.landing);
const Login = React.lazy(pageImports.login);
const Register = React.lazy(pageImports.register);
const Dashboard = React.lazy(pageImports.dashboard);
const Playbooks = React.lazy(pageImports.playbooks);
const PlaybookEditor = React.lazy(pageImports.playbookEditor);
const Billing = React.lazy(pageImports.billing);
const AuditLogs = React.lazy(pageImports.auditLogs);
const Team = React.lazy(pageImports.team);
const NotFound = React.lazy(pageImports.notFound);
const ClauseLibrary = React.lazy(pageImports.clauseLibrary);
const Analytics = React.lazy(pageImports.analytics);
const Compare = React.lazy(pageImports.compare);
const BatchUpload = React.lazy(pageImports.batchUpload);
const Executive = React.lazy(pageImports.executive);
const Reports = React.lazy(pageImports.reports);
const Marketplace = React.lazy(pageImports.marketplace);
const ForgotPassword = React.lazy(pageImports.forgotPassword);
const Drafting = React.lazy(pageImports.drafting);
const ConsentPreferences = React.lazy(pageImports.consentPreferences);
const DataRights = React.lazy(pageImports.dataRights);
const DPDPCommandCenter = React.lazy(pageImports.dpdpCommandCenter);
const Redline = React.lazy(pageImports.redline);

const protectedPageImports = [
  pageImports.dashboard,
  pageImports.playbooks,
  pageImports.playbookEditor,
  pageImports.redline,
  pageImports.drafting,
  pageImports.batchUpload,
  pageImports.clauseLibrary,
  pageImports.compare,
  pageImports.auditLogs,
  pageImports.marketplace,
  pageImports.dpdpCommandCenter,
];

let protectedChunksWarmed = false;


const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30000, // 30 seconds
      refetchOnWindowFocus: false,
    },
  },
});

function isAdminUser(user: User | null): boolean {
  return user?.role === 'admin' || user?.role === 'super_admin';
}

function RouteSpinner() {
  return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', backgroundColor: 'var(--bg-app)' }}>
    <div style={{ width: 32, height: 32, border: '2px solid var(--border)', borderTopColor: 'var(--accent)', borderRadius: '50%', animation: 'spin 0.7s linear infinite' }} />
  </div>;
}

function RouteChunkWarmup() {
  const location = useLocation();

  useEffect(() => {
    if (protectedChunksWarmed || !isAuthenticated()) return;
    protectedChunksWarmed = true;

    const timer = window.setTimeout(() => {
      void Promise.allSettled(protectedPageImports.map(loadPage => loadPage()));
    }, 1200);

    return () => window.clearTimeout(timer);
  }, [location.pathname]);

  return null;
}

// Protected route wrapper: render immediately from the stored login profile,
// then validate the HttpOnly cookie session in the background.
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const [authenticated, setAuthenticated] = useState(() => isAuthenticated());

  useEffect(() => {
    if (!isAuthenticated()) return;

    let active = true;
    validateSession()
      .then((user) => {
        if (!active) return;
        if (user) {
          setAuthenticated(true);
        } else {
          clearAuth();
          setAuthenticated(false);
        }
      })
      .catch(() => {
        if (!active) return;
        clearAuth();
        setAuthenticated(false);
      });

    return () => {
      active = false;
    };
  }, []);

  if (!authenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

// Admin-only route wrapper with server-side session + role validation
function AdminRoute({ children }: { children: React.ReactNode }) {
  const [validated, setValidated] = useState<'loading' | 'admin' | 'user' | 'unauthenticated'>(() => {
    const user = getStoredUser();
    if (!user) return 'unauthenticated';
    return isAdminUser(user) ? 'admin' : 'user';
  });

  useEffect(() => {
    if (!isAuthenticated()) return;

    let active = true;
    validateSession()
      .then((user) => {
        if (!active) return;
        if (isAdminUser(user)) {
          setValidated('admin');
        } else if (user) {
          setValidated('user');
        } else {
          clearAuth();
          setValidated('unauthenticated');
        }
      })
      .catch(() => {
        if (!active) return;
        clearAuth();
        setValidated('unauthenticated');
      });

    return () => {
      active = false;
    };
  }, []);

  if (validated === 'loading') {
    return <RouteSpinner />;
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
          <RouteChunkWarmup />
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
            <Route path="/compliance" element={<Navigate to="/dpdp" replace />} />
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
