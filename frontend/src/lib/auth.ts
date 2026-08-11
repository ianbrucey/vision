const TOKEN_KEY = "vision_token";
const USER_KEY = "vision_user";

export interface User {
  id: string;
  username: string;
  email: string | null;
  role: string;
  is_active: boolean;
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function getUser(): User | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try { return JSON.parse(raw); } catch { return null; }
}

export function setAuth(token: string, user: User) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
  // Broadcast so AuthProvider re-reads localStorage (same-tab login)
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event("vision-auth-change"));
  }
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function isAuthenticated(): boolean {
  return !!getToken();
}

export async function login(username: string, password: string) {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8400"}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Login failed" }));
    throw new Error(err.detail || "Login failed");
  }
  const data = await res.json();
  setAuth(data.token, data.user);
  return data.user as User;
}

export async function register(username: string, password: string, email?: string) {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8400"}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password, email }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Registration failed" }));
    throw new Error(err.detail || "Registration failed");
  }
  const data = await res.json();
  setAuth(data.token, data.user);
  return data.user as User;
}

export function logout() {
  clearAuth();
  if (typeof window !== "undefined") {
    window.location.href = "/login";
  }
}
