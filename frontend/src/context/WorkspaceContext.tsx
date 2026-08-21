import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import type { Workspace } from "../types";
import { workspaceService } from "../services/domainServices";
import { useAuth } from "./AuthContext";

interface WorkspaceContextType {
  workspace: Workspace | null;
  loading: boolean;
  refreshWorkspace: () => Promise<void>;
  updateLocalWorkspace: (ws: Workspace) => void;
}

const WorkspaceContext = createContext<WorkspaceContextType | undefined>(undefined);

export const WorkspaceProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user } = useAuth();
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const refreshWorkspace = useCallback(async () => {
    try {
      const res = await workspaceService.getWorkspace();
      if (res.success && res.data) {
        setWorkspace(res.data);
      }
    } catch (err) {
      console.warn("Could not fetch workspace", err);
    } finally {
      setLoading(false);
    }
  }, []);

  const updateLocalWorkspace = (ws: Workspace) => {
    setWorkspace(ws);
  };

  useEffect(() => {
    if (user) {
      refreshWorkspace();
    } else {
      setLoading(false);
    }
  }, [user, refreshWorkspace]);

  return (
    <WorkspaceContext.Provider
      value={{
        workspace,
        loading,
        refreshWorkspace,
        updateLocalWorkspace,
      }}
    >
      {children}
    </WorkspaceContext.Provider>
  );
};

export const useWorkspace = () => {
  const context = useContext(WorkspaceContext);
  if (!context) {
    throw new Error("useWorkspace must be used within a WorkspaceProvider");
  }
  return context;
};
