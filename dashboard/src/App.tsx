import React, { Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { isAuthenticated, isAdmin } from '@/api/client';

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


const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30000, // 30 seconds
      refetchOnWindowFocus: false,
    },
  },
});

// Protected route wrapper
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

// Admin-only route wrapper
function AdminRoute({ children }: { children: React.ReactNode }) {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }
  if (!isAdmin()) {
    return <Navigate to="/dashboard" replace />;
  }
  return <>{children}</>;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Suspense fallback={<div className="flex items-center justify-center min-h-screen"><div className="text-slate-400">Loading...</div></div>}>
          <Routes>
            {/* Public routes */}
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />

            {/* Protected routes - all authenticated users */}
            <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
            <Route path="/playbooks" element={<ProtectedRoute><Playbooks /></ProtectedRoute>} />
            <Route path="/clause-library" element={<ProtectedRoute><ClauseLibrary /></ProtectedRoute>} />
            <Route path="/templates" element={<ProtectedRoute><Templates /></ProtectedRoute>} />
            <Route path="/compare" element={<ProtectedRoute><Compare /></ProtectedRoute>} />
            <Route path="/audit-logs" element={<ProtectedRoute><AuditLogs /></ProtectedRoute>} />

            {/* Admin-only routes */}
            <Route path="/playbooks/:id" element={<AdminRoute><PlaybookEditor /></AdminRoute>} />
            <Route path="/analytics" element={<AdminRoute><Analytics /></AdminRoute>} />
            <Route path="/billing" element={<AdminRoute><Billing /></AdminRoute>} />
            <Route path="/team" element={<AdminRoute><Team /></AdminRoute>} />

            {/* Catch-all 404 */}
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
