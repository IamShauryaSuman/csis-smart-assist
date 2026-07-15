"use client";

import React, { createContext, useContext, useState, useCallback, useEffect } from "react";
import { api } from "@/lib/api";
import type { ChatSession } from "@/lib/types";

interface ChatContextValue {
  sessions: ChatSession[];
  loadingSessions: boolean;
  loadSessions: () => Promise<void>;
  createSession: () => Promise<ChatSession>;
  deleteSession: (id: string) => Promise<void>;
  renameSession: (id: string, title: string) => Promise<void>;
  pinSession: (id: string, isPinned: boolean) => Promise<void>;
  setSessions: React.Dispatch<React.SetStateAction<ChatSession[]>>;
}

const ChatContext = createContext<ChatContextValue | undefined>(undefined);

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [loadingSessions, setLoadingSessions] = useState(true);

  const loadSessions = useCallback(async () => {
    try {
      const data = await api.listSessions();
      setSessions(data);
    } catch (error) {
      console.error("Failed to load sessions:", error);
    } finally {
      setLoadingSessions(false);
    }
  }, []);

  const createSession = useCallback(async () => {
    try {
      const session = await api.createSession();
      setSessions((prev) => [session, ...prev]);
      return session;
    } catch (error) {
      console.error("Failed to create session:", error);
      throw error;
    }
  }, []);

  const deleteSession = useCallback(async (sessionId: string) => {
    try {
      await api.deleteSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
    } catch (error) {
      console.error("Failed to delete session:", error);
    }
  }, []);

  const renameSession = useCallback(async (sessionId: string, newTitle: string) => {
    try {
      const updated = await api.updateSession(sessionId, { title: newTitle });
      setSessions((prev) =>
        prev.map((s) => (s.id === sessionId ? { ...s, title: updated.title } : s))
      );
    } catch (error) {
      console.error("Failed to rename session:", error);
    }
  }, []);

  const pinSession = useCallback(async (sessionId: string, isPinned: boolean) => {
    try {
      const updated = await api.updateSession(sessionId, { is_pinned: isPinned });
      setSessions((prev) =>
        prev.map((s) => (s.id === sessionId ? { ...s, is_pinned: updated.is_pinned } : s))
      );
    } catch (error) {
      console.error("Failed to pin session:", error);
    }
  }, []);

  // Load sessions initially
  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  return (
    <ChatContext.Provider
      value={{
        sessions,
        loadingSessions,
        loadSessions,
        createSession,
        deleteSession,
        renameSession,
        pinSession,
        setSessions,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
}

export function useChatContext() {
  const context = useContext(ChatContext);
  if (context === undefined) {
    throw new Error("useChatContext must be used within a ChatProvider");
  }
  return context;
}
