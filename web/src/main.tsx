import "./index.css";
import { Component, ReactNode, StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import App from "./App";
import { queryClient } from "./lib/queryClient";

class RootErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null as Error | null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <div className="p-8 max-w-lg">
          <h1 className="text-lg font-semibold text-pp-navy">Permit Pilot failed to load</h1>
          <p className="mt-2 text-sm text-pp-muted">{this.state.error.message}</p>
          <a href="/login" className="pp-btn-primary inline-block mt-4">
            Reload sign in
          </a>
        </div>
      );
    }
    return this.props.children;
  }
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <RootErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </QueryClientProvider>
    </RootErrorBoundary>
  </StrictMode>,
);
