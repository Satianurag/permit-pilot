const TOKEN_KEY = "permit_pilot_token";
const USER_KEY = "permit_pilot_user";

export interface ClerkProfile {
  username: string;
  full_name: string;
  role: string;
}

export function getToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function getStoredUser(): ClerkProfile | null {
  const raw = sessionStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as ClerkProfile;
  } catch {
    return null;
  }
}

export function setToken(token: string): void {
  sessionStorage.setItem(TOKEN_KEY, token);
}

export function setSession(token: string, user: ClerkProfile): void {
  sessionStorage.setItem(TOKEN_KEY, token);
  sessionStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearSession(): void {
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(USER_KEY);
}

export function isAuthenticated(): boolean {
  return Boolean(getToken());
}

export function isAdmin(user: ClerkProfile | null): boolean {
  return user?.role === "admin";
}

