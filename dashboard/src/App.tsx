import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { isAuthenticated, isAdmin } from '@/api/client';
import Landing from '@/pages/Landing';
import Login from '@/pages/Login';
import Register from '@/pages/Register';
import Dashboard from '@/pages/Dashboard';
import Playbooks from '@/pages/Playbooks';
import PlaybookEditor from '@/pages/PlaybookEditor';
import Billing from '@/pages/Billing';
import AuditLogs from '@/pages/AuditLogs';
import Team from '@/pages/Team';


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
        <Routes>
          {/* Public routes */}
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          {/* Protected routes - all authenticated users */}
          <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/playbooks" element={<ProtectedRoute><Playbooks /></ProtectedRoute>} />
          <Route path="/audit-logs" element={<ProtectedRoute><AuditLogs /></ProtectedRoute>} />

          {/* Admin-only routes */}
          <Route path="/playbooks/:id" element={<AdminRoute><PlaybookEditor /></AdminRoute>} />
          <Route path="/billing" element={<AdminRoute><Billing /></AdminRoute>} />
          <Route path="/team" element={<AdminRoute><Team /></AdminRoute>} />

        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
