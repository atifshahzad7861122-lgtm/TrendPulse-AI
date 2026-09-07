import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import type { User } from "../types";
import { authService } from "../services/domainServices";

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  loading: boolean;
  login: (email: string, password: string, rememberMe?: boolean) => Promise<void>;
  logout: () => void;
  setSession: (token: string, user: User) => void;
  refreshProfile: () => Promise<void>;
  updateUser: (partialUser: Partial<User>) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem("trendpulse_token"));
  const [loading, setLoading] = useState<boolean>(true);

  const setSession = (newToken: string, newUser: User) => {
    localStorage.setItem("trendpulse_token", newToken);
    setToken(newToken);
    setUser(newUser);
  };

  const updateUser = useCallback((partialUser: Partial<User>) => {
    setUser((prev) => (prev ? { ...prev, ...partialUser } : null));
  }, []);

  const logout = () => {
    localStorage.removeItem("trendpulse_token");
    setToken(null);
    setUser(null);
    authService.logout().catch(() => {});
  };

  const refreshProfile = useCallback(async () => {
    const savedToken = localStorage.getItem("trendpulse_token");
    if (!savedToken) {
      setLoading(false);
      return;
    }
    try {
      const res = await authService.getMe();
      if (res.success && res.data) {
        setUser(res.data);
      } else {
        localStorage.removeItem("trendpulse_token");
        setToken(null);
        setUser(null);
      }
    } catch (err) {
      console.warn("Could not refresh user session", err);
      localStorage.removeItem("trendpulse_token");
      setToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const login = async (email: string, password: string, rememberMe?: boolean) => {
    const res = await authService.login({ email, password, remember_me: rememberMe });
    if (res.success && res.data) {
      const data = res.data;
      localStorage.setItem("trendpulse_token", data.access_token);
      setToken(data.access_token);
      setUser({
        id: data.user_id,
        email: data.email,
        full_name: data.full_name,
        is_verified: data.is_verified,
        workspace_id: data.workspace_id,
        role: data.role,
        avatar_url: data.avatar_url,
      });
    }
  };

  useEffect(() => {
    refreshProfile();
  }, [refreshProfile]);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user,
        loading,
        login,
        logout,
        setSession,
        refreshProfile,
        updateUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
