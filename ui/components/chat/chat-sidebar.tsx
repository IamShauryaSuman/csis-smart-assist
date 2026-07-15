"use client";

/**
 * ChatSidebar — Session history and management panel.
 *
 * Displays all chat sessions with active state highlighting,
 * new chat creation, and delete with hover-reveal.
 */

import { useState } from "react";
import Link from "next/link";
import { Pin, PinOff, Edit2, Trash2, MessageSquare, X, Plus } from "lucide-react";
import type { ChatSession } from "@/lib/types";
import styles from "./chat-sidebar.module.scss";

interface ChatSidebarProps {
  sessions: ChatSession[];
  activeSessionId: string | null;
  isOpen: boolean;
  onSelectSession?: () => void; // Used just to close sidebar on mobile
  onNewChat: () => void;
  onDeleteSession: (sessionId: string) => void;
  onRenameSession: (sessionId: string, newTitle: string) => void;
  onPinSession: (sessionId: string, isPinned: boolean) => void;
  onClose: () => void;
}

export default function ChatSidebar({
  sessions,
  activeSessionId,
  isOpen,
  onSelectSession,
  onNewChat,
  onDeleteSession,
  onRenameSession,
  onPinSession,
  onClose,
}: ChatSidebarProps) {
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return "Today";
    if (diffDays === 1) return "Yesterday";
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString("en-IN", {
      month: "short",
      day: "numeric",
    });
  };

  const handleStartEdit = (e: React.MouseEvent, session: ChatSession) => {
    e.preventDefault();
    e.stopPropagation();
    setEditingSessionId(session.id);
    setEditTitle(session.title);
  };

  const handleSaveEdit = (e: React.FormEvent | React.FocusEvent, sessionId: string) => {
    e.preventDefault();
    e.stopPropagation();
    if (editTitle.trim() && editTitle.trim() !== sessions.find(s => s.id === sessionId)?.title) {
      onRenameSession(sessionId, editTitle.trim());
    }
    setEditingSessionId(null);
  };

  const pinnedSessions = sessions.filter(s => s.is_pinned);
  const recentSessions = sessions.filter(s => !s.is_pinned);

  const renderSessionItem = (session: ChatSession) => {
    const isEditing = editingSessionId === session.id;

    const innerContent = (
      <>
        <div className={styles.sessionInfo}>
          {isEditing ? (
            <form onSubmit={(e) => handleSaveEdit(e, session.id)} className={styles.editForm}>
              <input
                type="text"
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                onBlur={(e) => handleSaveEdit(e, session.id)}
                autoFocus
                className={styles.editInput}
                onClick={(e) => e.preventDefault()}
              />
            </form>
          ) : (
            <div className={styles.sessionTitle}>{session.title}</div>
          )}
          <div className={styles.sessionDate}>
            {formatDate(session.updated_at)}
          </div>
        </div>

        <div className={styles.sessionActions}>
          <button
            className={styles.actionBtn}
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              onPinSession(session.id, !session.is_pinned);
            }}
            aria-label={session.is_pinned ? "Unpin chat" : "Pin chat"}
          >
            {session.is_pinned ? <PinOff size={14} /> : <Pin size={14} />}
          </button>
          {!isEditing && (
            <button
              className={styles.actionBtn}
              onClick={(e) => handleStartEdit(e, session)}
              aria-label="Rename chat"
            >
              <Edit2 size={14} />
            </button>
          )}
          <button
            className={`${styles.actionBtn} ${styles.actionBtnDanger}`}
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              onDeleteSession(session.id);
            }}
            aria-label="Delete chat"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </>
    );

    if (isEditing) {
      return (
        <div
          key={session.id}
          className={`${styles.sessionItem} ${
            session.id === activeSessionId ? styles.sessionItemActive : ""
          }`}
        >
          {innerContent}
        </div>
      );
    }

    return (
      <Link
        key={session.id}
        href={`/chat/${session.id}`}
        className={`${styles.sessionItem} ${
          session.id === activeSessionId ? styles.sessionItemActive : ""
        }`}
        onClick={onSelectSession}
      >
        {innerContent}
      </Link>
    );
  };

  return (
    <>
      {isOpen && <div className={styles.overlay} onClick={onClose} />}
      <aside className={`${styles.sidebar} ${isOpen ? styles.open : ""}`}>
        <div className={styles.header}>
          <span className={styles.title}>History</span>
          <button
            className={`${styles.newChatBtn} ${styles.desktopOnly}`}
            onClick={onNewChat}
            id="new-chat-btn"
            aria-label="New chat"
          >
            <Plus size={18} />
          </button>
          <button
            className={`${styles.closeSidebarBtn} ${styles.mobileOnly}`}
            onClick={onClose}
            aria-label="Close history"
          >
            <X size={20} />
          </button>
        </div>

        <div className={styles.list}>
          {sessions.length === 0 ? (
            <div className={styles.empty}>
              <span className={styles.emptyIcon}><MessageSquare size={32} /></span>
              <span className={styles.emptyText}>
                No conversations yet.
                <br />
                Start a new chat!
              </span>
            </div>
          ) : (
            <>
              {pinnedSessions.length > 0 && (
                <div className={styles.sessionGroup}>
                  <div className={styles.groupLabel}>Pinned</div>
                  {pinnedSessions.map(renderSessionItem)}
                </div>
              )}
              {recentSessions.length > 0 && (
                <div className={styles.sessionGroup}>
                  <div className={styles.groupLabel}>Recent</div>
                  {recentSessions.map(renderSessionItem)}
                </div>
              )}
            </>
          )}
        </div>
      </aside>
    </>
  );
}
