"use client";

import { useRouter } from "next/navigation";
import { useChatContext } from "@/lib/contexts/chat-context";
import { useChat } from "@/lib/hooks/useChat";
import dynamic from "next/dynamic";
const PolyhedronCanvas = dynamic(
  () => import("@/components/layout/polyhedron-canvas"),
  { ssr: false }
);
import ChatInput from "@/components/chat/chat-input";
import styles from "./page.module.scss";
import { useState } from "react";

export default function NewChatPage() {
  const router = useRouter();
  const { createSession } = useChatContext();
  const { sendMessage, sending } = useChat(null);
  const [mascotLoaded, setMascotLoaded] = useState(false);

  const handleSend = async (content: string) => {
    try {
      // Create a session first
      const session = await createSession();
      // Redirect to the new session and pass the initial message via URL
      router.push(`/chat/${session.id}?q=${encodeURIComponent(content)}`);
    } catch (error) {
      console.error("Failed to start new chat:", error);
    }
  };

  return (
    <>
      <div className={styles.messagesContainer}>
        <div className={`${styles.emptyState} ${mascotLoaded ? styles.ready : ""}`}>
          <div className={styles.mascotContainer}>
            <PolyhedronCanvas mode="mascot" onLoad={() => setMascotLoaded(true)} />
          </div>
          <h2 className={styles.emptyTitle}>How can I help you?</h2>
        </div>
      </div>

      <ChatInput onSend={handleSend} disabled={sending} />
    </>
  );
}
