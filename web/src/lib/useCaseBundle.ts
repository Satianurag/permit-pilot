import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, CaseBundle } from "./api";

export const caseKeys = {
  bundle: (id: string) => ["case-bundle", id] as const,
  context: (id: string) => ["case-context", id] as const,
  case: (id: string) => ["case", id] as const,
};

export function useCaseBundle(caseId: string) {
  return useQuery({
    queryKey: caseKeys.bundle(caseId),
    queryFn: ({ signal }) => api.getCaseBundle(caseId, { signal }),
    enabled: Boolean(caseId),
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return false;
      const checking = data.distribution.some((row) => row.status === "checking");
      const running = data.workflow.some((step) => step.status === "running" || step.status === "pending");
      return checking || running ? 4000 : false;
    },
  });
}

export function useCaseContext(caseId: string, enabled: boolean) {
  return useQuery({
    queryKey: caseKeys.context(caseId),
    queryFn: () => api.getCaseContext(caseId),
    enabled: enabled && Boolean(caseId),
  });
}

export function useInvalidateCase() {
  const client = useQueryClient();
  return (caseId?: string) =>
    Promise.all([
      caseId ? client.invalidateQueries({ queryKey: caseKeys.bundle(caseId) }) : Promise.resolve(),
      caseId ? client.invalidateQueries({ queryKey: caseKeys.context(caseId) }) : Promise.resolve(),
      client.invalidateQueries({ queryKey: ["tasks"] }),
      client.invalidateQueries({ queryKey: ["dashboard"] }),
      client.invalidateQueries({ queryKey: ["activity"] }),
      client.invalidateQueries({ queryKey: ["cases"] }),
    ]);
}

export type { CaseBundle };
