"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { get, post, tokens, type TokenPair } from "./api";
import type { User } from "./types";

type AuthState = {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<User>;
  loginWithGoogle: (idToken: string) => Promise<User>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    if (!tokens.access()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      setUser(await get<User>("/auth/me", true));
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshUser();
    // Keeps tabs (and the token store) in sync after login/logout.
    const onAuth = () => void refreshUser();
    window.addEventListener("eb:auth", onAuth);
    window.addEventListener("storage", onAuth);
    return () => {
      window.removeEventListener("eb:auth", onAuth);
      window.removeEventListener("storage", onAuth);
    };
  }, [refreshUser]);

  const login = useCallback<AuthState["login"]>(async (email, password) => {
    const pair = await post<TokenPair>("/auth/login", { email, password });
    tokens.save(pair);
    const me = await get<User>("/auth/me", true);
    setUser(me);
    setLoading(false);
    return me;
  }, []);

  const loginWithGoogle = useCallback<AuthState["loginWithGoogle"]>(async (idToken) => {
    const pair = await post<TokenPair>("/auth/oauth/google", { id_token: idToken });
    tokens.save(pair);
    const me = await get<User>("/auth/me", true);
    setUser(me);
    setLoading(false);
    return me;
  }, []);

  const logout = useCallback(async () => {
    const refresh = tokens.refresh();
    if (refresh) {
      // Best-effort: the local session is cleared even if the API is down.
      await post("/auth/logout", { refresh_token: refresh }).catch(() => undefined);
    }
    tokens.clear();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, loading, login, loginWithGoogle, logout, refreshUser }),
    [user, loading, login, loginWithGoogle, logout, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
