import React, { createContext, useContext, useEffect, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { api } from "./api";

/** RBAC roles as defined in CLAUDE.md */
export type UserRole =
  | "trainee"
  | "institute_admin"
  | "employer"
  | "planner"
  | "panel_member";

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  district_id: string;
  institute_id?: string | null;
}

interface AuthContextType {
  user: AuthUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<AuthUser>;
  quickLoginAsTrainee: () => Promise<AuthUser>;
  quickLoginAsInstituteAdmin: () => Promise<AuthUser>;
  quickLoginAsPanelMember: (email?: string) => Promise<AuthUser>;
  quickLoginAsPlanner: () => Promise<AuthUser>;
  quickLoginAsEmployer: () => Promise<AuthUser>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Rehydrate user from localStorage
    const savedUser = localStorage.getItem("vikas_user");
    const token = localStorage.getItem("access_token");

    if (savedUser && token) {
      try {
        setUser(JSON.parse(savedUser));
      } catch {
        localStorage.removeItem("vikas_user");
      }
    }
    setLoading(false);
  }, []);

  const login = async (email: string, password: string): Promise<AuthUser> => {
    // 1. Authenticate with backend
    const tokenData = await api<{ access_token: string; refresh_token: string }>(
      "/auth/login",
      {
        method: "POST",
        body: JSON.stringify({ email, password }),
      },
    );

    localStorage.setItem("access_token", tokenData.access_token);
    localStorage.setItem("refresh_token", tokenData.refresh_token);

    // 2. Fetch authenticated profile
    const profile = await api<AuthUser>("/auth/me", { method: "GET" });
    localStorage.setItem("vikas_user", JSON.stringify(profile));
    setUser(profile);
    return profile;
  };

  const quickLoginAsTrainee = async (): Promise<AuthUser> => {
    try {
      return await login("trainee@demo.vikas", "demo2026!");
    } catch {
      return login("trainee@dev.vikas", "devpass123");
    }
  };

  const quickLoginAsInstituteAdmin = async (): Promise<AuthUser> => {
    try {
      return await login("institute@demo.vikas", "demo2026!");
    } catch {
      return login("institute@dev.vikas", "devpass123");
    }
  };

  const quickLoginAsPanelMember = async (customEmail?: string): Promise<AuthUser> => {
    const targetEmail = customEmail || "panel@demo.vikas";
    try {
      return await login(targetEmail, "demo2026!");
    } catch {
      return login(customEmail || "panel@dev.vikas", "devpass123");
    }
  };

  const quickLoginAsPlanner = async (): Promise<AuthUser> => {
    try {
      return await login("planner@demo.vikas", "demo2026!");
    } catch {
      return login("planner@dev.vikas", "devpass123");
    }
  };

  const quickLoginAsEmployer = async (): Promise<AuthUser> => {
    try {
      return await login("employer@demo.vikas", "demo2026!");
    } catch {
      return login("employer@dev.vikas", "devpass123");
    }
  };

  const logout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("vikas_user");
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        quickLoginAsTrainee,
        quickLoginAsInstituteAdmin,
        quickLoginAsPanelMember,
        quickLoginAsPlanner,
        quickLoginAsEmployer,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

/**
 * Route guard ensuring the user is logged in with the specified role.
 */
export function RequireRole({
  role,
  children,
}: {
  role: UserRole;
  children: React.ReactNode;
}) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-slate-50">
        <div className="flex flex-col items-center gap-2">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-emerald-600 border-t-transparent" />
          <p className="text-sm font-medium text-slate-600">Verifying session...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (user.role !== role) {
    return (
      <div className="flex h-screen w-full flex-col items-center justify-center p-6 text-center">
        <div className="max-w-md rounded-xl border border-red-200 bg-red-50 p-6">
          <h2 className="text-lg font-bold text-red-800">Access Restricted</h2>
          <p className="mt-2 text-sm text-red-600">
            Your current role ({user.role}) is not authorized to view this trainee portal.
          </p>
          <button
            onClick={() => {
              localStorage.clear();
              window.location.href = "/login";
            }}
            className="mt-4 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
          >
            Switch Account
          </button>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}

