"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ChatProvider, useChatContext } from "@/lib/contexts/chat-context";
import { PanelLeft, Plus } from "lucide-react";
import ChatSidebar from "@/components/chat/chat-sidebar";
import styles from "./page.module.scss";

// We need an inner component to consume the context
function ChatLayoutInner({ children }: { children: React.ReactNode }) {
  const { sessions, createSession, deleteSession, renameSession, pinSession } = useChatContext();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const router = useRouter();
  const params = useParams();
  
  // Extract id from /chat/[id]
  const activeSessionId = Array.isArray(params?.id) ? params.id[0] : params?.id || null;

  const handleNewChat = () => {
    setSidebarOpen(false);
    router.push("/chat");
  };

  const handleDeleteSession = async (sessionId: string) => {
    await deleteSession(sessionId);
    if (activeSessionId === sessionId) {
      router.push("/chat");
    }
  };

  return (
    <div className={styles.chatLayout}>
      <ChatSidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        isOpen={sidebarOpen}
        onSelectSession={() => setSidebarOpen(false)} // Handled by Link navigation now
        onNewChat={handleNewChat}
        onDeleteSession={handleDeleteSession}
        onRenameSession={renameSession}
        onPinSession={pinSession}
        onClose={() => setSidebarOpen(false)}
      />

      <div className={styles.mainArea}>
        <div className={styles.mobileChatHeader}>
          <button onClick={() => setSidebarOpen(true)} className={styles.headerBtn} aria-label="Open chat history">
            <PanelLeft size={20} />
          </button>
          <button onClick={handleNewChat} className={styles.headerBtn} aria-label="New chat">
            <Plus size={20} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

export default function ChatLayout({ children }: { children: React.ReactNode }) {
  return (
    <ChatProvider>
      <ChatLayoutInner>{children}</ChatLayoutInner>
    </ChatProvider>
  );
}
