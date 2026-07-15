"use client";

import { useCallback, useState, useEffect } from "react";
import { api } from "@/lib/api";
import type { Message } from "@/lib/types";
import { useChatContext } from "@/lib/contexts/chat-context";

export function useChat(sessionId: string | null) {
  const { sessions, setSessions, loadSessions } = useChatContext();
  
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [lastIntent, setLastIntent] = useState<string>("");

  // Load messages whenever the sessionId changes
  useEffect(() => {
    if (sessionId) {
      const fetchMessages = async () => {
        setLoading(true);
        try {
          const data = await api.getSessionMessages(sessionId);
          setMessages((prev) => {
            // Prevent race condition: if the user just sent a message (e.g., from the 'q' URL param),
            // the local state will have optimistic messages. If this DB fetch resolves afterward 
            // (often with empty data because the insert hasn't finished), do NOT overwrite.
            const hasOptimistic = prev.some(
              (m) => m.id.startsWith("temp-") || m.id.startsWith("tmp-asst-") || m.id.startsWith("user-")
            );
            if (hasOptimistic) {
              return prev;
            }
            return data;
          });
        } catch (error) {
          console.error("Failed to load messages:", error);
          setMessages([]);
        } finally {
          setLoading(false);
        }
      };
      fetchMessages();
    } else {
      setMessages([]);
    }
  }, [sessionId]);

  const sendMessage = useCallback(
    async (content: string, targetSessionId: string | null = sessionId) => {
      if (!targetSessionId) {
        console.error("Cannot send message without a session ID");
        return;
      }

      // Optimistically add user message to the UI
      const optimisticUserMsg: Message = {
        id: `temp-${Date.now()}`,
        session_id: targetSessionId,
        role: "user",
        content,
        interactive_type: null,
        interactive_payload: null,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, optimisticUserMsg]);
      setSending(true);

      let assistantMsgId = `tmp-asst-${Date.now()}`;
      try {
        
        // Add an empty assistant message to be filled
        const emptyAssistantMsg: Message = {
          id: assistantMsgId,
          session_id: targetSessionId,
          role: "assistant",
          content: "",
          interactive_type: null,
          interactive_payload: null,
          created_at: new Date().toISOString(),
        };

        setMessages((prev) => {
          const withoutOptimistic = prev.filter(
            (m) => m.id !== optimisticUserMsg.id
          );
          return [
            ...withoutOptimistic,
            { ...optimisticUserMsg, id: `user-${Date.now()}` },
            emptyAssistantMsg,
          ];
        });

        await api.sendMessageStream(
          targetSessionId,
          content,
          (meta) => {
            setLastIntent(meta.intent);
            if (meta.message_id) {
              assistantMsgId = meta.message_id;
            }
            if (meta.interactive_type) {
              setMessages((prev) => prev.map(m => 
                m.id === emptyAssistantMsg.id 
                  ? { ...m, interactive_type: meta.interactive_type, interactive_payload: meta.interactive_payload } 
                  : m
              ));
            }
          },
          (textChunk) => {
            setMessages((prev) => prev.map(m => 
              m.id === emptyAssistantMsg.id 
                ? { ...m, content: m.content + textChunk } 
                : m
            ));
          },
          (err) => {
            console.error("Streaming error:", err);
            throw err;
          }
        );

        // Update the timestamp to when the response finished streaming
        setMessages((prev) => prev.map(m => 
          m.id === emptyAssistantMsg.id 
            ? { ...m, created_at: new Date().toISOString() } 
            : m
        ));

        // Get the current session to check its title
        const currentSession = sessions.find(s => s.id === targetSessionId);
        const currentTitle = currentSession?.title || "New Chat";

        // Poll for title update if we are in a "New Chat"
        if (currentTitle === "New Chat" || currentTitle === "New Chat Session") {
          let attempts = 0;
          const pollInterval = setInterval(async () => {
            attempts++;
            if (attempts > 5) {
              clearInterval(pollInterval);
              return;
            }
            try {
              const data = await api.listSessions();
              const updatedSession = data.find(s => s.id === targetSessionId);
              if (updatedSession && updatedSession.title !== "New Chat" && updatedSession.title !== "New Chat Session") {
                setSessions(data);
                clearInterval(pollInterval);
              }
            } catch (e) {
              // Ignore errors during polling
            }
          }, 2000);
        } else {
          // If not a new chat, just reload once to ensure sync (e.g. updated_at timestamp)
          setTimeout(() => loadSessions(), 1000);
        }
      } catch (error: any) {
        console.error("Failed to send message:", error);
        
        // Remove the empty assistant placeholder bubble on failure
        setMessages((prev) => {
          const filtered = prev.filter((m) => m.id !== assistantMsgId);
          return [
            ...filtered,
            {
              id: `error-${Date.now()}`,
              session_id: targetSessionId,
              role: "assistant",
              content: `**Error:** ${error.message || "I encountered an issue processing your message. Please try again."}`,
              interactive_type: null,
              interactive_payload: null,
              created_at: new Date().toISOString(),
            },
          ];
        });
      } finally {
        setSending(false);
      }
    },
    [sessionId, sessions, setSessions, loadSessions]
  );

  return {
    messages,
    loading,
    sending,
    lastIntent,
    sendMessage,
  };
}
