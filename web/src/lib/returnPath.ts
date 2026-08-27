const RETURN_KEY = "permit_pilot_return";

export function saveReturnPath(path: string): void {
  try {
    sessionStorage.setItem(RETURN_KEY, path);
  } catch {
    /* private mode */
  }
}

export function consumeReturnPath(fallback = "/dashboard"): string {
  try {
    const path = sessionStorage.getItem(RETURN_KEY);
    sessionStorage.removeItem(RETURN_KEY);
    if (path && path !== "/login") return path;
  } catch {
    /* private mode */
  }
  return fallback;
}
