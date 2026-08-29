import { lazy, Suspense, useEffect } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import AppShell from "./components/AppShell";
import { ToastProvider } from "./components/Toast";
import { isAuthenticated } from "./lib/auth";
import LoginPage from "./pages/LoginPage";

const CasePage = lazy(() => import("./pages/CasePage"));
const DossiersPage = lazy(() => import("./pages/DossiersPage"));
const IntakePage = lazy(() => import("./pages/IntakePage"));
const MorePage = lazy(() => import("./pages/MorePage"));
const NotFoundPage = lazy(() => import("./pages/NotFoundPage"));
const TasksPage = lazy(() => import("./pages/TasksPage"));
const AgentsPage = lazy(() => import("./pages/AgentsPage"));
const GovernancePage = lazy(() => import("./pages/GovernancePage"));
const MemoryPage = lazy(() => import("./pages/MemoryPage"));
const TracesPage = lazy(() => import("./pages/TracesPage"));
const ActivityPage = lazy(() => import("./pages/ActivityPage"));
const DashboardPage = lazy(() => import("./pages/DashboardPage"));

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  return children;
}

function RouteFallback() {
  return <p className="p-8 text-sm text-pp-muted">Loading workspace…</p>;
}

function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return null;
}

export default function App() {
  return (
    <ToastProvider>
      <ScrollToTop />
      <Suspense fallback={<RouteFallback />}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            element={
              <ProtectedRoute>
                <AppShell />
              </ProtectedRoute>
            }
          >
            <Route path="/" element={<Navigate to="/work" replace />} />
            <Route path="/work" element={<TasksPage />} />
            <Route path="/find" element={<DossiersPage />} />
            <Route path="/intake" element={<IntakePage />} />
            <Route path="/more" element={<MorePage />} />
            <Route path="/more/departments" element={<AgentsPage />} />
            <Route path="/more/security" element={<GovernancePage />} />
            <Route path="/more/property-notes" element={<MemoryPage />} />
            <Route path="/more/history" element={<TracesPage />} />
            <Route path="/more/activity" element={<ActivityPage />} />
            <Route path="/more/metrics" element={<DashboardPage />} />
            <Route path="/dashboard" element={<Navigate to="/work" replace />} />
            <Route path="/tasks" element={<Navigate to="/work" replace />} />
            <Route path="/permits" element={<Navigate to="/find" replace />} />
            <Route path="/agents" element={<Navigate to="/more/departments" replace />} />
            <Route path="/governance" element={<Navigate to="/more/security" replace />} />
            <Route path="/memory" element={<Navigate to="/more/property-notes" replace />} />
            <Route path="/traces" element={<Navigate to="/more/history" replace />} />
            <Route path="/activity" element={<Navigate to="/more/activity" replace />} />
            <Route path="/cases/:id" element={<CasePage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Route>
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </Suspense>
    </ToastProvider>
  );
}
