export function caseBackTarget(from: string | null): { to: string; label: string } {
  switch (from) {
    case "search":
      return { to: "/permits", label: "permit search" };
    case "activity":
      return { to: "/activity", label: "activity" };
    case "dashboard":
      return { to: "/dashboard", label: "dashboard" };
    default:
      return { to: "/tasks", label: "tasks" };
  }
}
