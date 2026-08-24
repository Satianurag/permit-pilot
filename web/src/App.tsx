import { useState } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import AgentCatalog from "./components/AgentCatalog";
import AppShell from "./components/AppShell";
import CasePage from "./pages/CasePage";
import TasksPage from "./pages/TasksPage";

export default function App() {
  const [agentsOpen, setAgentsOpen] = useState(false);
  const location = useLocation();
  const agentsCaseId = location.pathname.match(/^\/cases\/([^/]+)/)?.[1];

  return (
    <>
      <Routes>
        <Route element={<AppShell onOpenAgents={() => setAgentsOpen(true)} />}>
          <Route path="/" element={<Navigate to="/tasks" replace />} />
          <Route path="/tasks" element={<TasksPage />} />
          <Route path="/cases/:id" element={<CasePage onOpenAgents={() => setAgentsOpen(true)} />} />
        </Route>
      </Routes>
      <AgentCatalog open={agentsOpen} onClose={() => setAgentsOpen(false)} caseId={agentsCaseId} />
    </>
  );
}
