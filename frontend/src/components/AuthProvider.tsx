"use client";

import { createContext, useContext, useEffect, useState, useRef, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { getToken, getUser, clearAuth, type User } from "@/lib/auth";

interface AuthState {
  user: User | null;
  ready: boolean;
  logout: () => void;
}

const AuthContext = createContext<AuthState>({ user: null, ready: false, logout: () => {} });

export function useAuth() {
  return useContext(AuthContext);
}

const PUBLIC_PATHS = ["/login", "/register"];

function isPublicPath(pathname: string): boolean {
  if (pathname === "/") return true;
  return PUBLIC_PATHS.some((p) => pathname.startsWith(p));
}

export default function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const pathname = usePathname();
  const router = useRouter();

  // Restore session from localStorage (runs once on mount)
  const restoredRef = useRef(false);
  useEffect(() => {
    if (restoredRef.current) return;
    restoredRef.current = true;
    /* eslint-disable react-hooks/set-state-in-effect */
    const stored = getUser();
    const token = getToken();
    if (stored && token) setUser(stored);
    setReady(true);
    /* eslint-enable react-hooks/set-state-in-effect */
  }, []);

  useEffect(() => {
    if (!ready || !pathname) return;
    const isPublic = isPublicPath(pathname);
    const authed = !!getToken();

    if (!authed && !isPublic) {
      router.replace("/login");
    } else if (authed && isPublic && pathname !== "/solicitations") {
      router.replace("/solicitations");
    }
  }, [pathname, ready, router]);

  const handleLogout = () => {
    setUser(null);
    clearAuth();
    router.replace("/");
  };

  return (
    <AuthContext.Provider value={{ user, ready, logout: handleLogout }}>
      {children}
    </AuthContext.Provider>
  );
}
