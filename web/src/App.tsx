import { lazy, Suspense, useEffect } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import AppShell from "./components/AppShell";
import { ToastProvider } from "./components/Toast";
import { isAuthenticated } from "./lib/auth";
import LoginPage from "./pages/LoginPage";

const ActivityPage = lazy(() => import("./pages/ActivityPage"));
const AgentsPage = lazy(() => import("./pages/AgentsPage"));
const CasePage = lazy(() => import("./pages/CasePage"));
const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const DossiersPage = lazy(() => import("./pages/DossiersPage"));
const GovernancePage = lazy(() => import("./pages/GovernancePage"));
const MemoryPage = lazy(() => import("./pages/MemoryPage"));
const NotFoundPage = lazy(() => import("./pages/NotFoundPage"));
const TasksPage = lazy(() => import("./pages/TasksPage"));
const TracesPage = lazy(() => import("./pages/TracesPage"));

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
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/activity" element={<ActivityPage />} />
            <Route path="/tasks" element={<TasksPage />} />
            <Route path="/permits" element={<DossiersPage />} />
            <Route path="/agents" element={<AgentsPage />} />
            <Route path="/governance" element={<GovernancePage />} />
            <Route path="/memory" element={<MemoryPage />} />
            <Route path="/traces" element={<TracesPage />} />
            <Route path="/cases/:id" element={<CasePage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Route>
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </Suspense>
    </ToastProvider>
  );
}
