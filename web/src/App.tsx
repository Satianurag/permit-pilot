import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import AppShell from "./components/AppShell";
import { ToastProvider } from "./components/Toast";
import { isAuthenticated } from "./lib/auth";
import ActivityPage from "./pages/ActivityPage";
import AgentsPage from "./pages/AgentsPage";
import CasePage from "./pages/CasePage";
import DashboardPage from "./pages/DashboardPage";
import DossiersPage from "./pages/DossiersPage";
import LoginPage from "./pages/LoginPage";
import NotFoundPage from "./pages/NotFoundPage";
import TasksPage from "./pages/TasksPage";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  return children;
}

export default function App() {
  return (
    <ToastProvider>
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
          <Route path="/cases/:id" element={<CasePage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </ToastProvider>
  );
}
