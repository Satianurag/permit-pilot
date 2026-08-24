import { useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import AgentCatalog from "./components/AgentCatalog";
import AppShell from "./components/AppShell";
import { isAuthenticated } from "./lib/auth";
import CasePage from "./pages/CasePage";
import DossiersPage from "./pages/DossiersPage";
import LoginPage from "./pages/LoginPage";
import TasksPage from "./pages/TasksPage";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

export default function App() {
  const [agentsOpen, setAgentsOpen] = useState(false);

  return (
    <>
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
        </Route>
      </Routes>
      <AgentCatalog open={agentsOpen} onClose={() => setAgentsOpen(false)} />
    </>
  );
}
