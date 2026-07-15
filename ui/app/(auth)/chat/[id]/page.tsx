"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useSearchParams, useRouter } from "next/navigation";
import { useAuth } from "@/lib/hooks/useAuth";
import { useProfile } from "@/lib/hooks/useProfile";
import { useChat } from "@/lib/hooks/useChat";
import { useBookings } from "@/lib/hooks/useBookings";
import { ArrowDown } from "lucide-react";
import { api } from "@/lib/api";
import dynamic from "next/dynamic";
const PolyhedronCanvas = dynamic(
  () => import("@/components/layout/polyhedron-canvas"),
  { ssr: false }
);
import ChatBubble from "@/components/chat/chat-bubble";
import ChatInput from "@/components/chat/chat-input";
import BookingProposal from "@/components/bookings/booking-proposal";
import type { BookingProposalPayload } from "@/lib/types";
import styles from "../page.module.scss"; // Reuse styles from parent

const processedSessions = new Set<string>();

export default function ChatSessionPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const sessionId = Array.isArray(params?.id) ? params.id[0] : params?.id || null;

  const { user } = useAuth();
  const { profile } = useProfile(user?.id);
  const { bookings, loadBookings, createBooking, lockBooking, unlockBooking, updateBookingDetails } = useBookings(user?.id);
  const { messages, loading, sending, sendMessage } = useChat(sessionId);
  const [mascotLoaded, setMascotLoaded] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesSentThisSession = useRef(0);

  // Intercept sendMessage to track if user sent anything during this component mount
  const handleSendMessage = async (content: string) => {
    messagesSentThisSession.current += 1;
    await sendMessage(content);
  };

  useEffect(() => {
    const q = searchParams?.get("q");
    if (q && sessionId && !processedSessions.has(sessionId)) {
      processedSessions.add(sessionId);
      
      // Synchronously clear the URL to prevent any strict mode race conditions
      if (typeof window !== "undefined") {
        window.history.replaceState(null, "", window.location.pathname);
      }
      
      handleSendMessage(q);
    }
  }, [sessionId, searchParams, router]);

  useEffect(() => {
    if (user?.id) {
      loadBookings();
    }
  }, [loadBookings, user?.id]);

  // Memory synthesis is temporarily disabled to prevent React Strict Mode 
  // from exhausting the Gemini API Free Tier quota on unmounts.

  const [showScrollButton, setShowScrollButton] = useState(false);
  const isInitialScroll = useRef(true);

  // Reset initial scroll flag on session change
  useEffect(() => {
    isInitialScroll.current = true;
  }, [sessionId]);

  // Auto-scroll to bottom on new messages or to latest chat on load
  useEffect(() => {
    if (messages.length > 0) {
      if (isInitialScroll.current) {
        // Find the last user message to scroll to the "start" of the latest chat
        const lastUserMsg = [...messages].reverse().find(m => m.role === "user");
        if (lastUserMsg) {
          const el = document.getElementById(`msg-${lastUserMsg.id}`);
          if (el) {
            el.scrollIntoView({ behavior: "auto", block: "start" });
          } else {
            messagesEndRef.current?.scrollIntoView({ behavior: "auto" });
          }
        } else {
          messagesEndRef.current?.scrollIntoView({ behavior: "auto" });
        }
        
        setTimeout(() => {
          isInitialScroll.current = false;
        }, 500);
      } else {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
      }
    }
  }, [messages]);

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const { scrollTop, scrollHeight, clientHeight } = e.currentTarget;
    setShowScrollButton(scrollHeight - scrollTop - clientHeight > 150);
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const userInitials =
    profile?.full_name
      ?.split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase()
      .slice(0, 2) || "U";

  const lastDraftMessageId = [...messages].reverse().find((m) => m.interactive_type === "booking_proposal")?.id;

  return (
    <>
      <div className={styles.messagesContainer} onScroll={handleScroll}>
        {messages.length === 0 && !loading ? (
          <div className={`${styles.emptyState} ${mascotLoaded ? styles.ready : ""}`}>
            <div className={styles.mascotContainer}>
              <PolyhedronCanvas mode="mascot" onLoad={() => setMascotLoaded(true)} />
            </div>
            <h2 className={styles.emptyTitle}>How can I help you?</h2>
          </div>
        ) : (
          <>
            {messages.map((msg) => (
              <div key={msg.id} id={`msg-${msg.id}`}>
                <ChatBubble message={msg} userInitials={userInitials} />
                {msg.interactive_type === "booking_proposal" &&
                  msg.interactive_payload &&
                  user && (
                    <div style={{ paddingLeft: "52px" }}>
                      <BookingProposal
                        payload={
                          msg.interactive_payload as unknown as BookingProposalPayload
                        }
                        bookings={bookings}
                        isLatestDraft={msg.id === lastDraftMessageId}
                        onCreateBooking={createBooking}
                        onLockBooking={lockBooking}
                        onUnlockBooking={unlockBooking}
                        onUpdateBooking={updateBookingDetails}
                      />
                    </div>
                  )}
              </div>
            ))}

            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      <div className={styles.scrollBtnContainer}>
        {showScrollButton && (
          <button onClick={scrollToBottom} className={styles.scrollBottomBtn} aria-label="Scroll to bottom">
            <ArrowDown size={16} />
          </button>
        )}
      </div>

      <ChatInput onSend={(content) => sendMessage(content)} disabled={sending || !sessionId} />
    </>
  );
}
