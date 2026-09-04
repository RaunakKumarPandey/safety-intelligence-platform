export interface UserSession {
  email: string;
  role: "employee" | "officer";
  name: string;
  loggedInAt: number;
}

export const AUTH_STORAGE_KEY = "safetyai_user_session";

export function getStoredUser(): UserSession | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as UserSession;
  } catch (e) {
    return null;
  }
}

export function setStoredUser(user: UserSession): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(user));
  } catch (e) {
    console.error("Failed to store user session:", e);
  }
}

export function clearStoredUser(): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.removeItem(AUTH_STORAGE_KEY);
  } catch (e) {
    console.error("Failed to clear user session:", e);
  }
}

export function isUserAuthenticated(): boolean {
  return !!getStoredUser();
}

export function isSafetyOfficer(user?: UserSession | null): boolean {
  const u = user !== undefined ? user : getStoredUser();
  return u?.role === "officer";
}

export function isEmployee(user?: UserSession | null): boolean {
  const u = user !== undefined ? user : getStoredUser();
  return u?.role === "employee";
}
