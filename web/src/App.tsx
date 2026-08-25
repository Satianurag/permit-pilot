import { useState } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import AgentCatalog from "./components/AgentCatalog";
import AppShell from "./components/AppShell";
import { ToastProvider } from "./components/Toast";
import { isAuthenticated } from "./lib/auth";
import CasePage from "./pages/CasePage";
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
  const [agentsOpen, setAgentsOpen] = useState(false);

  return (
    <ToastProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          element={
            <ProtectedRoute>
              <AppShell onOpenAgents={() => setAgentsOpen(true)} />
            </ProtectedRoute>
          }
        >
          <Route path="/" element={<Navigate to="/tasks" replace />} />
          <Route path="/tasks" element={<TasksPage />} />
          <Route path="/permits" element={<DossiersPage />} />
          <Route path="/cases/:id" element={<CasePage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
      <AgentCatalog open={agentsOpen} onClose={() => setAgentsOpen(false)} />
    </ToastProvider>
  );
}
