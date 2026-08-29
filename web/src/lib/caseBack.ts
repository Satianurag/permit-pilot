export function caseBackTarget(from: string | null): { to: string; label: string } {
  switch (from) {
    case "search":
    case "find":
      return { to: "/find", label: "Find a case" };
    case "activity":
      return { to: "/more/history", label: "history" };
    case "dashboard":
    case "work":
    case "tasks":
      return { to: "/work", label: "My work" };
    default:
      return { to: "/work", label: "My work" };
  }
}