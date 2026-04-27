"use client";

import { useSession, signIn, signOut } from "next-auth/react";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: { name: string; link: string; excerpt: string }[];
  calendarFlow?: CalendarFlow;
}

type CalendarSlot = {
  start_iso: string;
  end_iso: string;
  duration_minutes: number;
  location?: string | null;
};

type CalendarFlow = {
  status: "slot_available" | "slot_unavailable" | "missing_datetime";
  requested_slot?: CalendarSlot | null;
  nearby_slots?: CalendarSlot[];
  requires_user_approval?: boolean;
};

interface ChatSession {
  id: string;
  title: string;
  updatedAt: string;
  messages: Message[];
}

type BookingRequest = {
  id: string;
  email: string;
  location: string;
  date: string;
  time: string;
  purpose: string;
  remarks: string;
  status: "pending" | "accepted" | "declined";
};

type BackendBookingRequest = {
  id: string;
  requester_user_id: string;
  location: string;
  date: string;
  time_slot: string;
  purpose: string;
  remarks: string | null;
  status: "pending" | "accepted" | "declined";
};

type SyncedUserPayload = {
  user?: {
    id?: string;
    email?: string;
    full_name?: string | null;
  };
  roles?: string[];
};

const backendUrl =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

const initialBookingRequests: BookingRequest[] = [];

const formatHistoryTime = (isoDate: string) => {
  const value = new Date(isoDate);
  const now = new Date();

  const sameDay =
    value.getFullYear() === now.getFullYear() &&
    value.getMonth() === now.getMonth() &&
    value.getDate() === now.getDate();

  if (sameDay) {
    return value.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  return value.toLocaleDateString([], {
    month: "short",
    day: "numeric",
  });
};

function HomePage() {
  const { data: session, status } = useSession();
  const [userRoles, setUserRoles] = useState<string[]>([]);
  const [syncedUserId, setSyncedUserId] = useState<string | null>(null);
  const isAdmin = userRoles.includes("admin");

  const [chatSessions, setChatSessions] = useState<ChatSession[]>([]);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [bookingRequests, setBookingRequests] = useState<BookingRequest[]>(
    initialBookingRequests,
  );

  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSessionsLoading, setIsSessionsLoading] = useState(false);
  const [isBookingActionLoading, setIsBookingActionLoading] = useState(false);
  const [actionedMessageIds, setActionedMessageIds] = useState<Set<string>>(
    new Set(),
  );
  const [isIngesting, setIsIngesting] = useState(false);
  const [lastIngestSummary, setLastIngestSummary] = useState<any | null>(null);
  const [ingestError, setIngestError] = useState<string | null>(null);
  const [bookingPurposes, setBookingPurposes] = useState<
    Record<string, string>
  >({});
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);

  const sortedChatSessions = [...chatSessions].sort(
    (left, right) =>
      new Date(right.updatedAt).getTime() - new Date(left.updatedAt).getTime(),
  );

  const activeChat = useMemo(
    () =>
      chatSessions.find((chatSession) => chatSession.id === activeChatId) ??
      chatSessions[0] ??
      null,
    [activeChatId, chatSessions],
  );

  const messages = activeChat?.messages ?? [];

  const toBookingSlotPayload = (slot: CalendarSlot) => {
    const start = new Date(slot.start_iso);
    const end = new Date(slot.end_iso);

    const pad = (n: number) => n.toString().padStart(2, "0");
    const fmt = (d: Date) => `${pad(d.getHours())}:${pad(d.getMinutes())}`;

    return {
      date: start.toISOString().split("T")[0],
      time_slot: `${fmt(start)}-${fmt(end)}`,
    };
  };

  const appendAssistantMessage = (content: string) => {
    if (!activeChat) return;
    setChatSessions((previous) =>
      previous.map((chatSession) => {
        if (chatSession.id !== activeChat.id) return chatSession;
        return {
          ...chatSession,
          updatedAt: new Date().toISOString(),
          messages: [
            ...chatSession.messages,
            {
              id: crypto.randomUUID(),
              role: "assistant",
              content,
            },
          ],
        };
      }),
    );
  };

  const createBookingFromSlot = async (
    slot: CalendarSlot,
    messageId: string,
  ) => {
    const requesterId = syncedUserId || session?.user?.email;
    if (!requesterId) {
      appendAssistantMessage(
        "Please sign in first to create a booking request.",
      );
      return;
    }

    const purpose = (bookingPurposes[messageId] || "").trim();
    if (!purpose) {
      appendAssistantMessage(
        "Please enter the **purpose** for this booking before approving.",
      );
      return;
    }

    setIsBookingActionLoading(true);
    try {
      const bookingSlot = toBookingSlotPayload(slot);
      const response = await fetch(`${backendUrl}/booking-requests`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          requester_user_id: requesterId,
          location: slot.location || "Calendar Room",
          date: bookingSlot.date,
          time_slot: bookingSlot.time_slot,
          purpose: purpose,
          remarks: "Created via SmartAssist chatbot",
        }),
      });

      if (!response.ok) {
        const errorBody = await response.text().catch(() => "");
        console.error("Booking request failed:", response.status, errorBody);
        throw new Error(`Failed to create booking request: ${response.status}`);
      }

      const created = (await response.json()) as {
        id?: string;
        status?: string;
      };
      const confirmationMessage = `Booking request created successfully${created.id ? ` (ID: ${created.id})` : ""}. Status: ${created.status ?? "pending"}.`;
      appendAssistantMessage(confirmationMessage);

      // Persist confirmation message to backend
      if (activeChatId) {
        await fetch(`${backendUrl}/chat/sessions/${activeChatId}/messages`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            role: "assistant",
            content: confirmationMessage,
          }),
        }).catch((err) =>
          console.error("Failed to persist confirmation message:", err),
        );
      }

      // Persist actioned state in backend message metadata
      if (activeChatId) {
        await fetch(
          `${backendUrl}/chat/sessions/${activeChatId}/messages/${messageId}`,
          {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              metadata: { is_actioned: true },
            }),
          },
        ).catch((err) =>
          console.error("Failed to update message metadata:", err),
        );
      }
    } catch (err) {
      console.error("Booking creation error:", err);
      const errorMessage =
        "I could not create the booking request right now. Please try again.";
      appendAssistantMessage(errorMessage);

      // Also persist error message to backend
      if (activeChatId) {
        await fetch(`${backendUrl}/chat/sessions/${activeChatId}/messages`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            role: "assistant",
            content: errorMessage,
          }),
        }).catch((err) =>
          console.error("Failed to persist error message:", err),
        );
      }
    } finally {
      setIsBookingActionLoading(false);
    }
  };

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeChat?.id, messages?.length, isLoading]);

  // Sync user roles
  useEffect(() => {
    if (!session?.user?.email) {
      setUserRoles([]);
      setSyncedUserId(null);
      return;
    }
    const syncSessionUser = async () => {
      try {
        const response = await fetch(`${backendUrl}/users/sync-session`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: session.user?.email,
            full_name: session.user?.name,
          }),
        });
        if (!response.ok) throw new Error("Failed to sync user");
        const payload = (await response.json()) as SyncedUserPayload;
        setSyncedUserId(payload.user?.id ?? null);
        setUserRoles(payload.roles ?? []);
      } catch {
        setSyncedUserId(null);
        setUserRoles([]);
      }
    };
    syncSessionUser();
  }, [session?.user?.email]);

  // Load chat sessions from backend
  useEffect(() => {
    if (!session?.user?.email) return;

    let cancelled = false;
    const loadSessions = async () => {
      setIsSessionsLoading(true);
      try {
        const response = await fetch(
          `${backendUrl}/chat/sessions?email=${encodeURIComponent(session.user!.email!)}`,
        );
        if (!response.ok) return;
        const data = (await response.json()) as {
          id: string;
          title: string;
          updated_at: string;
        }[];
        const loaded: ChatSession[] = data.map((s) => ({
          id: s.id,
          title: s.title,
          updatedAt: s.updated_at,
          messages: [],
        }));
        if (cancelled) return;
        setChatSessions((prev) => {
          // Merge: keep messages from already-loaded sessions
          const existingById = new Map(prev.map((s) => [s.id, s]));
          return loaded.map((s) => {
            const existing = existingById.get(s.id);
            return existing && existing.messages.length > 0
              ? { ...s, messages: existing.messages }
              : s;
          });
        });
        if (loaded.length > 0) {
          setActiveChatId(loaded[0].id);
        } else {
          // Auto-create first session for new users
          const createRes = await fetch(`${backendUrl}/chat/sessions`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              user_email: session.user!.email,
              title: "New chat",
            }),
          });
          if (createRes.ok) {
            const created = (await createRes.json()) as {
              id: string;
              title: string;
              updated_at: string;
            };
            const newChat: ChatSession = {
              id: created.id,
              title: created.title,
              updatedAt: created.updated_at,
              messages: [],
            };
            setChatSessions([newChat]);
            setActiveChatId(newChat.id);
          }
        }
      } catch {
      } finally {
        setIsSessionsLoading(false);
      }
    };

    loadSessions();
    return () => {
      cancelled = true;
    };
  }, [session?.user?.email]);

  // Load messages when active session changes
  useEffect(() => {
    if (!activeChatId) return;
    // Skip if messages are already loaded for this session
    const current = chatSessions.find((s) => s.id === activeChatId);
    if (current && current.messages.length > 0) return;

    const loadMessages = async () => {
      try {
        const response = await fetch(
          `${backendUrl}/chat/sessions/${activeChatId}/messages`,
        );
        if (!response.ok) return;
        const data = (await response.json()) as {
          id: string;
          role: "user" | "assistant";
          content: string;
          metadata: Record<string, unknown>;
        }[];
        const msgs: Message[] = data.map((m) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          calendarFlow:
            (m.metadata?.calendar_flow as CalendarFlow) ?? undefined,
          citations: [],
        }));
        setChatSessions((prev) =>
          prev.map((s) =>
            s.id === activeChatId ? { ...s, messages: msgs } : s,
          ),
        );

        const actionedIds = data
          .filter((m) => (m.metadata as Record<string, unknown>)?.is_actioned)
          .map((m) => m.id);
        if (actionedIds.length > 0) {
          setActionedMessageIds((prev) => {
            const next = new Set(prev);
            actionedIds.forEach((id) => next.add(id));
            return next;
          });
        }
      } catch {}
    };

    loadMessages();
  }, [activeChatId]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!session || !isAdmin) return;

    const loadRequests = async () => {
      try {
        const response = await fetch(`${backendUrl}/booking-requests`);
        if (!response.ok) return;
        const data = (await response.json()) as BackendBookingRequest[];
        setBookingRequests(
          data.map((request) => ({
            id: request.id,
            email: request.requester_user_id,
            location: request.location,
            date: request.date,
            time: request.time_slot,
            purpose: request.purpose,
            remarks: request.remarks ?? "",
            status: request.status,
          })),
        );
      } catch {}
    };

    loadRequests();
  }, [isAdmin, session]);

  const createNewChat = async () => {
    if (isLoading || !session?.user?.email) return;

    try {
      const response = await fetch(`${backendUrl}/chat/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_email: session.user.email,
          title: "New chat",
        }),
      });

      if (!response.ok) return;
      const created = (await response.json()) as {
        id: string;
        title: string;
        updated_at: string;
      };

      const newChat: ChatSession = {
        id: created.id,
        title: created.title,
        updatedAt: created.updated_at,
        messages: [],
      };

      setChatSessions((previous) => [newChat, ...previous]);
      setActiveChatId(newChat.id);
      setInput("");
    } catch {}
  };

  const handleSendMessage = (event: FormEvent) => {
    event.preventDefault();
    if (!input.trim() || isLoading || !activeChat) return;

    const now = new Date().toISOString();
    const currentChatId = activeChat.id;
    const userInput = input.trim();
    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: userInput,
    };

    setChatSessions((previous) =>
      previous.map((chatSession) => {
        if (chatSession.id !== currentChatId) return chatSession;

        const firstUserMessage = chatSession.messages.find(
          (message) => message.role === "user",
        );

        return {
          ...chatSession,
          title: firstUserMessage
            ? chatSession.title
            : userInput.slice(0, 36) || "New chat",
          updatedAt: now,
          messages: [...chatSession.messages, userMessage],
        };
      }),
    );

    setInput("");
    setIsLoading(true);

    (async () => {
      try {
        const response = await fetch(`${backendUrl}/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            query: userInput,
            user_id: session?.user?.email ?? "anonymous",
            session_id: currentChatId,
          }),
        });

        if (!response.ok) {
          let detail =
            "Backend chat is unavailable right now. Please try again.";
          try {
            const errorPayload = (await response.json()) as { detail?: string };
            if (errorPayload?.detail) {
              detail = errorPayload.detail;
            }
          } catch {
            // Keep default message
          }
          throw new Error(detail);
        }

        const payload = (await response.json()) as {
          answer: string;
          intent: "info_query" | "calendar_query";
          calendar_flow?: CalendarFlow;
          sources?: { document_id?: string; similarity?: number }[];
          assistant_message_id?: string;
        };

        const botResponse: Message = {
          id: payload.assistant_message_id ?? (Date.now() + 1).toString(),
          role: "assistant",
          content: payload.answer,
          calendarFlow: payload.calendar_flow,
          citations: [],
        };

        setChatSessions((previous) =>
          previous.map((chatSession) => {
            if (chatSession.id !== currentChatId) return chatSession;

            return {
              ...chatSession,
              updatedAt: new Date().toISOString(),
              messages: [...chatSession.messages, botResponse],
            };
          }),
        );
      } catch (error) {
        const message =
          error instanceof Error && error.message
            ? error.message
            : "Backend chat is unavailable right now. Please try again.";
        const fallbackResponse: Message = {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: message,
        };

        setChatSessions((previous) =>
          previous.map((chatSession) => {
            if (chatSession.id !== currentChatId) return chatSession;
            return {
              ...chatSession,
              updatedAt: new Date().toISOString(),
              messages: [...chatSession.messages, fallbackResponse],
            };
          }),
        );
      } finally {
        setIsLoading(false);
      }
    })();
  };

  const requestStatusColor = (requestStatus: BookingRequest["status"]) => {
    if (requestStatus === "accepted") return "text-success";
    if (requestStatus === "declined") return "text-danger";
    return "text-pending";
  };

  const handleRemarksChange = (requestId: string, remarks: string) => {
    setBookingRequests((previous) =>
      previous.map((request) =>
        request.id === requestId ? { ...request, remarks } : request,
      ),
    );
  };

  const handleRequestDecision = (
    requestId: string,
    decision: "accepted" | "declined",
  ) => {
    const selected = bookingRequests.find(
      (request) => request.id === requestId,
    );
    if (!selected || selected.status !== "pending") return;

    setBookingRequests((previous) =>
      previous.map((request) =>
        request.id === requestId ? { ...request, status: decision } : request,
      ),
    );

    (async () => {
      try {
        const response = await fetch(
          `${backendUrl}/booking-requests/${requestId}/decision`,
          {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              status: decision,
              remarks: selected.remarks,
              reviewer_user_id: syncedUserId,
            }),
          },
        );

        if (!response.ok) {
          throw new Error("Failed to save decision");
        }
      } catch {
        setBookingRequests((previous) =>
          previous.map((request) =>
            request.id === requestId
              ? { ...request, status: "pending" }
              : request,
          ),
        );
      }
    })();
  };

  if (status === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-bg-base font-mono text-text-secondary">
        Initializing...
      </div>
    );
  }

  if (!session) {
    return (
      <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-bg-base px-4 text-center">
        {/* Animated Polyhedron Sphere Background */}
        <div className="pointer-events-none absolute inset-0 z-0 flex items-center justify-center overflow-hidden opacity-20">
          <svg
            className="w-[1200px] max-w-[200vw] animate-spin"
            viewBox="0 0 200 200"
            xmlns="http://www.w3.org/2000/svg"
            style={{ animationDuration: "120s" }}
          >
            <g stroke="currentColor" strokeWidth="0.5" fill="none" className="text-text-secondary opacity-70">
              {/* Outer boundary */}
              <circle cx="100" cy="100" r="90" />
              
              {/* Geodesic/Polyhedron style intersecting geometric lines */}
              <polygon points="10,100 40,40 100,10 160,40 190,100 160,160 100,190 40,160" />
              <polygon points="28,56 64,28 136,28 172,56 172,144 136,172 64,172 28,144" />
              <polygon points="46,100 64,64 100,46 136,64 154,100 136,136 100,154 64,136" />
              
              {/* Cross sections */}
              <line x1="100" y1="10" x2="100" y2="190" />
              <line x1="10" y1="100" x2="190" y2="100" />
              <line x1="36" y1="36" x2="164" y2="164" />
              <line x1="36" y1="164" x2="164" y2="36" />
              
              {/* Vertical and horizontal chords */}
              <line x1="64" y1="28" x2="64" y2="172" />
              <line x1="136" y1="28" x2="136" y2="172" />
              <line x1="28" y1="56" x2="172" y2="56" />
              <line x1="28" y1="144" x2="172" y2="144" />

              {/* Triangle meshes to create 3D illusion */}
              <path d="M100 10 L64 64 L100 100 L136 64 Z" />
              <path d="M100 190 L64 136 L100 100 L136 136 Z" />
              <path d="M10 100 L64 64 L100 100 L64 136 Z" />
              <path d="M190 100 L136 64 L100 100 L136 136 Z" />
              
              {/* Vertices/Points */}
              <g fill="currentColor" stroke="none">
                <circle cx="100" cy="10" r="1.5" />
                <circle cx="100" cy="190" r="1.5" />
                <circle cx="10" cy="100" r="1.5" />
                <circle cx="190" cy="100" r="1.5" />
                
                <circle cx="36" cy="36" r="1.5" />
                <circle cx="164" cy="164" r="1.5" />
                <circle cx="36" cy="164" r="1.5" />
                <circle cx="164" cy="36" r="1.5" />
                
                <circle cx="40" cy="40" r="1.5" />
                <circle cx="160" cy="40" r="1.5" />
                <circle cx="160" cy="160" r="1.5" />
                <circle cx="40" cy="160" r="1.5" />
                
                <circle cx="28" cy="56" r="1.5" />
                <circle cx="172" cy="56" r="1.5" />
                <circle cx="172" cy="144" r="1.5" />
                <circle cx="28" cy="144" r="1.5" />
                
                <circle cx="64" cy="28" r="1.5" />
                <circle cx="136" cy="28" r="1.5" />
                <circle cx="136" cy="172" r="1.5" />
                <circle cx="64" cy="172" r="1.5" />
                
                <circle cx="46" cy="100" r="1.5" />
                <circle cx="154" cy="100" r="1.5" />
                <circle cx="100" cy="46" r="1.5" />
                <circle cx="100" cy="154" r="1.5" />
                
                <circle cx="64" cy="64" r="1.5" />
                <circle cx="136" cy="64" r="1.5" />
                <circle cx="136" cy="136" r="1.5" />
                <circle cx="64" cy="136" r="1.5" />
                
                <circle cx="100" cy="100" r="2" />
              </g>
            </g>
          </svg>
        </div>

        <div className="z-10 flex w-full max-w-xl flex-col items-center rounded-xl border border-border bg-bg-surface bg-opacity-5 p-8 backdrop-blur-sm md:p-12 shadow-2xl">
          <div className="mb-3 font-mono text-xl tracking-[0.2em] text-text-primary md:text-2xl">
            CSIS
          </div>
          <h1 className="font-display text-4xl font-bold tracking-tight text-accent md:text-5xl">
            SmartAssist
          </h1>
          <p className="mt-3 font-mono text-xs uppercase tracking-widest text-text-secondary md:mt-4 md:text-sm">
            BITS Pilani, K K Birla Goa Campus
          </p>
          
          <div className="my-8 h-px w-24 bg-border" />
          
          <p className="max-w-sm text-sm text-text-secondary md:text-base leading-relaxed">
            Secure campus assistant with document-grounded responses and smart
            booking requests.
          </p>
          
          <button
            onClick={() => signIn("google")}
            className="mt-10 border border-accent bg-accent/10 px-8 py-3.5 font-mono text-sm font-semibold tracking-wider text-accent transition-all hover:bg-accent hover:text-bg-base hover:shadow-[0_0_15px_rgba(128,252,104,0.3)]"
          >
            SIGN IN WITH GOOGLE
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="relative flex h-[100dvh] w-full flex-col overflow-hidden bg-bg-base text-text-primary">
      {/* Animated Polyhedron Sphere Background */}
      <div className="pointer-events-none absolute inset-0 z-0 flex items-center justify-center overflow-hidden opacity-30">
        <svg
          className="w-[1200px] max-w-[200vw] animate-spin"
          viewBox="0 0 200 200"
          xmlns="http://www.w3.org/2000/svg"
          style={{ animationDuration: "120s" }}
        >
          <g stroke="currentColor" strokeWidth="0.5" fill="none" className="text-text-secondary opacity-100">
            {/* Outer boundary */}
            <circle cx="100" cy="100" r="90" />
            
            {/* Geodesic/Polyhedron style intersecting geometric lines */}
            <polygon points="10,100 40,40 100,10 160,40 190,100 160,160 100,190 40,160" />
            <polygon points="28,56 64,28 136,28 172,56 172,144 136,172 64,172 28,144" />
            <polygon points="46,100 64,64 100,46 136,64 154,100 136,136 100,154 64,136" />
            
            {/* Cross sections */}
            <line x1="100" y1="10" x2="100" y2="190" />
            <line x1="10" y1="100" x2="190" y2="100" />
            <line x1="36" y1="36" x2="164" y2="164" />
            <line x1="36" y1="164" x2="164" y2="36" />
            
            {/* Vertical and horizontal chords */}
            <line x1="64" y1="28" x2="64" y2="172" />
            <line x1="136" y1="28" x2="136" y2="172" />
            <line x1="28" y1="56" x2="172" y2="56" />
            <line x1="28" y1="144" x2="172" y2="144" />

            {/* Triangle meshes to create 3D illusion */}
            <path d="M100 10 L64 64 L100 100 L136 64 Z" />
            <path d="M100 190 L64 136 L100 100 L136 136 Z" />
            <path d="M10 100 L64 64 L100 100 L64 136 Z" />
            <path d="M190 100 L136 64 L100 100 L136 136 Z" />
            
            {/* Vertices/Points */}
            <g fill="currentColor" stroke="none">
              <circle cx="100" cy="10" r="1.5" />
              <circle cx="100" cy="190" r="1.5" />
              <circle cx="10" cy="100" r="1.5" />
              <circle cx="190" cy="100" r="1.5" />
              
              <circle cx="36" cy="36" r="1.5" />
              <circle cx="164" cy="164" r="1.5" />
              <circle cx="36" cy="164" r="1.5" />
              <circle cx="164" cy="36" r="1.5" />
              
              <circle cx="40" cy="40" r="1.5" />
              <circle cx="160" cy="40" r="1.5" />
              <circle cx="160" cy="160" r="1.5" />
              <circle cx="40" cy="160" r="1.5" />
              
              <circle cx="28" cy="56" r="1.5" />
              <circle cx="172" cy="56" r="1.5" />
              <circle cx="172" cy="144" r="1.5" />
              <circle cx="28" cy="144" r="1.5" />
              
              <circle cx="64" cy="28" r="1.5" />
              <circle cx="136" cy="28" r="1.5" />
              <circle cx="136" cy="172" r="1.5" />
              <circle cx="64" cy="172" r="1.5" />
              
              <circle cx="46" cy="100" r="1.5" />
              <circle cx="154" cy="100" r="1.5" />
              <circle cx="100" cy="46" r="1.5" />
              <circle cx="100" cy="154" r="1.5" />
              
              <circle cx="64" cy="64" r="1.5" />
              <circle cx="136" cy="64" r="1.5" />
              <circle cx="136" cy="136" r="1.5" />
              <circle cx="64" cy="136" r="1.5" />
              
              <circle cx="100" cy="100" r="2" />
            </g>
          </g>
        </svg>
      </div>

        <header className="relative z-10 flex-shrink-0 border-b border-border bg-bg-surface/50 backdrop-blur-md px-4 py-3 md:px-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="font-display text-lg font-semibold md:text-xl">
            CSIS SmartAssist
          </h1>
          <div className="flex items-center gap-3 text-xs md:text-sm">
            <span className="font-mono text-text-secondary">
              {session.user?.email}
            </span>
            <button
              onClick={() => signOut()}
              className="border border-danger px-2 py-1 font-mono text-danger hover:bg-danger/10"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      {isAdmin ? (
        <main className="relative z-10 w-full flex-1 overflow-y-auto px-4 py-4 md:px-6 md:py-6">
          <div className="mb-4 border border-border bg-bg-surface/60 backdrop-blur-md px-4 py-3 shadow-lg">
            <h2 className="font-display text-lg font-semibold md:text-xl">
              Booking Requests Dashboard
            </h2>
            <p className="mt-1 text-sm text-text-secondary">
              Review pending requests and add remarks before accepting or
              declining.
            </p>
            <div className="mt-3 space-y-2">
              <div className="flex items-center gap-2">
                <button
                  onClick={async () => {
                    try {
                      setIsIngesting(true);
                      setIngestError(null);
                      const resp = await fetch(
                        `${backendUrl}/rag/ingest-drive`,
                        {
                          method: "POST",
                          headers: { "Content-Type": "application/json" },
                          body: JSON.stringify({}),
                        },
                      );
                      if (!resp.ok) {
                        const text = await resp.text().catch(() => "");
                        throw new Error(text || `Status ${resp.status}`);
                      }
                      const summary = await resp.json();
                      setLastIngestSummary(summary);
                    } catch (err: any) {
                      setIngestError(err?.message || String(err));
                    } finally {
                      setIsIngesting(false);
                    }
                  }}
                  disabled={isIngesting}
                  className="border border-accent px-3 py-2 font-mono text-xs text-accent transition hover:bg-accent/10 disabled:opacity-60"
                >
                  {isIngesting ? "Running..." : "Run Drive Ingest"}
                </button>
              </div>
              <div className="text-sm text-text-secondary">
                {ingestError ? (
                  <span className="text-danger">{ingestError}</span>
                ) : null}
              </div>
            </div>
            {lastIngestSummary && (
              <div className="mt-3 rounded border border-border bg-bg-base p-3 text-sm">
                <p>Folder: {lastIngestSummary.folder_id ?? "(server)"}</p>
                <p>Processed: {lastIngestSummary.processed_files}</p>
                <p>Ingested: {lastIngestSummary.ingested_files}</p>
                <p>Chunks written: {lastIngestSummary.chunks_written}</p>
                {lastIngestSummary.errors &&
                  lastIngestSummary.errors.length > 0 && (
                    <details className="mt-2 text-xs text-text-secondary">
                      <summary>
                        Errors ({lastIngestSummary.errors.length})
                      </summary>
                      <ul className="list-disc pl-4">
                        {lastIngestSummary.errors.map(
                          (e: string, i: number) => (
                            <li key={i}>{e}</li>
                          ),
                        )}
                      </ul>
                    </details>
                  )}
              </div>
            )}
          </div>

          <div className="ui-scrollbar max-h-[calc(100vh-190px)] space-y-3 overflow-y-auto pr-1">
            {bookingRequests.map((request) => (
              <article
                key={request.id}
                className="border border-border bg-bg-surface/60 backdrop-blur-md p-4 shadow-lg"
              >
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border pb-2">
                  <p className="font-mono text-sm text-text-secondary">
                    {request.id}
                  </p>
                  <p
                    className={`font-mono text-xs uppercase ${requestStatusColor(request.status)}`}
                  >
                    {request.status}
                  </p>
                </div>

                <div className="mt-3 grid gap-2 text-sm md:grid-cols-2">
                  <p>
                    <span className="font-mono text-text-secondary">
                      Email:
                    </span>{" "}
                    {request.email}
                  </p>
                  <p>
                    <span className="font-mono text-text-secondary">
                      Location:
                    </span>{" "}
                    {request.location}
                  </p>
                  <p>
                    <span className="font-mono text-text-secondary">Date:</span>{" "}
                    {request.date}
                  </p>
                  <p>
                    <span className="font-mono text-text-secondary">Time:</span>{" "}
                    {request.time}
                  </p>
                  <p>
                    <span className="font-mono text-text-secondary">
                      Purpose:
                    </span>{" "}
                    {request.purpose}
                  </p>
                </div>

                <div className="mt-3">
                  <label
                    htmlFor={`remarks-${request.id}`}
                    className="mb-1 block font-mono text-xs text-text-secondary"
                  >
                    Remarks
                  </label>
                  <textarea
                    id={`remarks-${request.id}`}
                    value={request.remarks}
                    onChange={(event) =>
                      handleRemarksChange(request.id, event.target.value)
                    }
                    rows={3}
                    className="w-full resize-y border border-border bg-bg-base px-3 py-2 text-sm text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-1 focus:ring-link"
                    placeholder="Add remarks for this booking request..."
                  />
                </div>

                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    onClick={() =>
                      handleRequestDecision(request.id, "accepted")
                    }
                    disabled={request.status !== "pending"}
                    className="border border-success px-3 py-2 font-mono text-xs text-success transition hover:bg-success/10 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    Accept
                  </button>
                  <button
                    onClick={() =>
                      handleRequestDecision(request.id, "declined")
                    }
                    disabled={request.status !== "pending"}
                    className="border border-danger px-3 py-2 font-mono text-xs text-danger transition hover:bg-danger/10 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    Decline
                  </button>
                </div>
              </article>
            ))}
          </div>
        </main>
      ) : (
        <main className="relative z-10 flex w-full flex-1 flex-col overflow-hidden min-h-0 lg:grid lg:grid-cols-12">
          <aside
            id="history-sidebar"
            className={`${isHistoryOpen ? "flex" : "hidden"} h-[40vh] min-h-0 shrink-0 flex-col overflow-hidden border-b border-border lg:h-auto lg:col-span-3 lg:flex lg:border-b-0 lg:border-r bg-bg-surface bg-opacity-10 backdrop-blur-sm`}
          >
            <div className="flex items-center justify-between border-b border-border bg-bg-surface/50 backdrop-blur-md px-4 py-2 font-mono text-sm text-text-secondary">
              <span>History</span>
              <button
                onClick={createNewChat}
                disabled={isLoading}
                className="border border-border px-2 py-1 text-[11px] text-text-primary transition hover:bg-bg-base disabled:cursor-not-allowed disabled:opacity-60"
              >
                + New
              </button>
            </div>

            <div className="ui-scrollbar min-h-0 flex-1 space-y-1 overflow-y-auto px-2 py-2">
              {sortedChatSessions.map((chatSession) => {
                const isActive = chatSession.id === activeChatId;

                return (
                  <button
                    key={chatSession.id}
                    onClick={() => {
                      if (isLoading) return;
                      setActiveChatId(chatSession.id);
                      setInput("");
                    }}
                    className={`flex w-full items-start justify-between gap-3 border px-3 py-2 text-left transition ${
                      isActive
                        ? "border-accent bg-bg-surface/60 backdrop-blur-sm"
                        : "border-border hover:bg-bg-surface/40 hover:backdrop-blur-sm"
                    }`}
                  >
                    <span className="min-w-0 flex-1 truncate text-sm text-text-primary">
                      {chatSession.title}
                    </span>
                    <span className="shrink-0 font-mono text-[11px] text-text-secondary">
                      {formatHistoryTime(chatSession.updatedAt)}
                    </span>
                  </button>
                );
              })}
            </div>
          </aside>

          <section className="flex flex-1 flex-col overflow-hidden border-b border-border bg-bg-surface bg-opacity-5 backdrop-blur-sm lg:col-span-9 lg:min-h-0 lg:border-b-0 lg:border-r">
            <div className="flex items-center justify-between border-b border-border bg-bg-surface/50 backdrop-blur-md px-4 py-2 font-mono text-sm text-text-secondary md:px-6">
              <span>Chat</span>
              <div className="flex items-center gap-2 lg:hidden">
                <button
                  onClick={() => setIsHistoryOpen((previous) => !previous)}
                  className="border border-border px-2 py-1 text-[11px] text-text-primary transition hover:bg-bg-base"
                  aria-expanded={isHistoryOpen}
                  aria-controls="history-sidebar"
                >
                  {isHistoryOpen ? "Hide History" : "Show History"}
                </button>
              </div>
            </div>
            <div className="ui-scrollbar flex-1 overflow-y-auto px-4 py-4 md:px-6">
              {messages?.map((message) => (
                <article
                  key={message.id}
                  className="border-b border-border py-4"
                >
                  <p className="font-mono text-xs text-text-secondary md:text-sm">
                    {message.role === "user" ? "You" : "Assistant"}
                  </p>
                  {message.role === "assistant" ? (
                    <div className="mt-1 text-sm leading-relaxed md:text-base [&_a]:text-link [&_a]:underline [&_blockquote]:border-l-2 [&_blockquote]:border-border [&_blockquote]:bg-bg-surface/50 [&_blockquote]:backdrop-blur-sm [&_blockquote]:px-3 [&_blockquote]:py-2 [&_code]:rounded [&_code]:bg-bg-surface/50 [&_code]:px-1 [&_code]:py-0.5 [&_ol]:list-decimal [&_ol]:pl-5 [&_ol]:space-y-1 [&_ul]:list-disc [&_ul]:pl-5 [&_ul]:space-y-1 [&_h1]:mt-2 [&_h1]:text-base [&_h1]:font-semibold [&_h2]:mt-2 [&_h2]:text-base [&_h2]:font-semibold [&_h3]:mt-2 [&_h3]:text-sm [&_h3]:font-semibold [&_p]:whitespace-pre-wrap [&_p]:mb-2 [&_p:last-child]:mb-0">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {message.content}
                      </ReactMarkdown>
                    </div>
                  ) : (
                    <p className="mt-1 whitespace-pre-wrap text-sm leading-relaxed md:text-base">
                      {message.content}
                    </p>
                  )}

                  {message.citations && message.citations.length > 0 && (
                    <div className="mt-3 space-y-2 border border-border bg-bg-surface/40 backdrop-blur-md p-3">
                      {message.citations.map((citation, index) => (
                        <div
                          key={`${message.id}-${index}`}
                          className="text-xs md:text-sm"
                        >
                          <p className="font-mono text-text-primary">
                            Source: {citation.name}
                          </p>
                          <a
                            href={citation.link}
                            className="font-mono text-link hover:underline"
                          >
                            {citation.link}
                          </a>
                          <blockquote className="mt-1 border-l-2 border-border bg-bg-base px-2 py-1 text-text-secondary">
                            {citation.excerpt}
                          </blockquote>
                        </div>
                      ))}
                    </div>
                  )}

                  {message.role === "assistant" &&
                    message.calendarFlow?.status === "slot_available" &&
                    message.calendarFlow.requested_slot && (
                      <div className="mt-3 space-y-2">
                        <div>
                          <label
                            htmlFor={`purpose-${message.id}`}
                            className="mb-1 block font-mono text-xs text-text-secondary"
                          >
                            Purpose (required)
                          </label>
                          <input
                            id={`purpose-${message.id}`}
                            type="text"
                            value={bookingPurposes[message.id] || ""}
                            onChange={(e) =>
                              setBookingPurposes((prev) => ({
                                ...prev,
                                [message.id]: e.target.value,
                              }))
                            }
                            disabled={actionedMessageIds.has(message.id)}
                            placeholder="e.g. Extra Tutorial, Lab session, Meeting..."
                            className="w-full border border-border bg-bg-base px-3 py-2 text-sm text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-1 focus:ring-link disabled:opacity-60"
                          />
                        </div>
                        <div className="flex flex-wrap gap-2">
                          <button
                            onClick={() => {
                              setActionedMessageIds((prev) =>
                                new Set(prev).add(message.id),
                              );
                              createBookingFromSlot(
                                message.calendarFlow!
                                  .requested_slot as CalendarSlot,
                                message.id,
                              );
                            }}
                            disabled={
                              isBookingActionLoading ||
                              actionedMessageIds.has(message.id)
                            }
                            className="border border-success px-3 py-2 font-mono text-xs text-success transition hover:bg-success/10 disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            {actionedMessageIds.has(message.id)
                              ? "Request submitted"
                              : isBookingActionLoading
                                ? "Creating request..."
                                : "Approve and create request"}
                          </button>
                          <button
                            onClick={() => {
                              setActionedMessageIds((prev) =>
                                new Set(prev).add(message.id),
                              );
                              appendAssistantMessage(
                                "Understood. I did not create the booking request.",
                              );
                            }}
                            disabled={
                              isBookingActionLoading ||
                              actionedMessageIds.has(message.id)
                            }
                            className="border border-danger px-3 py-2 font-mono text-xs text-danger transition hover:bg-danger/10 disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            Decline
                          </button>
                        </div>
                      </div>
                    )}

                  {message.role === "assistant" &&
                    (message.calendarFlow?.status === "slot_unavailable" ||
                      message.calendarFlow?.status === "missing_datetime") &&
                    (message.calendarFlow?.nearby_slots?.length ?? 0) > 0 && (
                      <div className="mt-3 space-y-2 border border-border bg-bg-surface/40 backdrop-blur-md p-3">
                        <p className="font-mono text-xs text-text-secondary">
                          Select a nearby free slot to create a booking request:
                        </p>
                        <div className="flex flex-wrap gap-2">
                          {message.calendarFlow?.nearby_slots?.map(
                            (slot, index) => {
                              const start = new Date(slot.start_iso);
                              const end = new Date(slot.end_iso);
                              return (
                                <button
                                  key={`${message.id}-slot-${index}`}
                                  onClick={() =>
                                    createBookingFromSlot(slot, message.id)
                                  }
                                  disabled={isBookingActionLoading}
                                  className="border border-accent px-3 py-2 font-mono text-xs text-accent transition hover:bg-accent/10 disabled:cursor-not-allowed disabled:opacity-60"
                                >
                                  {start.toLocaleDateString([], {
                                    month: "short",
                                    day: "numeric",
                                  })}{" "}
                                  {start.toLocaleTimeString([], {
                                    hour: "2-digit",
                                    minute: "2-digit",
                                  })}
                                  {" - "}
                                  {end.toLocaleTimeString([], {
                                    hour: "2-digit",
                                    minute: "2-digit",
                                  })}
                                </button>
                              );
                            },
                          )}
                        </div>
                      </div>
                    )}
                </article>
              ))}

              {isLoading && (
                <div className="border-b border-border py-4 font-mono text-sm text-text-secondary">
                  Thinking...
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            <div className="sticky bottom-0 border-t border-border bg-bg-surface/50 backdrop-blur-md px-4 py-3 md:px-6">
              <form onSubmit={handleSendMessage} className="flex gap-2">
                <input
                  type="text"
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  disabled={isLoading}
                  placeholder="Ask about policies, citations, or room booking..."
                  className="h-11 flex-1 border border-border bg-bg-surface bg-opacity-20 backdrop-blur-sm px-3 text-sm text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-1 focus:ring-link disabled:opacity-60"
                />
                <button
                  type="submit"
                  disabled={isLoading || !input.trim()}
                  className="h-11 border border-accent bg-accent px-4 font-mono text-xs font-semibold text-bg-base transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  Send
                </button>
              </form>
            </div>
          </section>
        </main>
      )}
    </div>
  );
}

export default dynamic(() => Promise.resolve(HomePage), { ssr: false });
