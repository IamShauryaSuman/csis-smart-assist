"use client";

import { useSession, signIn, signOut } from "next-auth/react";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: { name: string; link: string; excerpt: string }[];
}

interface ChatSession {
  id: string;
  title: string;
  updatedAt: string;
  messages: Message[];
}

type Slot = {
  id: string;
  resource: string;
  date: string;
  time: string;
  status: "available" | "limited" | "unavailable";
  alternates?: string[];
};

type BookingRequest = {
  id: string;
  requester: string;
  resource: string;
  date: string;
  time: string;
  purpose: string;
  participants: number;
  remarks: string;
  status: "pending" | "accepted" | "declined";
};

const initialSlots: Slot[] = [
  {
    id: "LIB-A-1000",
    resource: "Library A",
    date: "2026-03-02",
    time: "10:00-11:00",
    status: "available",
  },
  {
    id: "LIB-A-1100",
    resource: "Library A",
    date: "2026-03-02",
    time: "11:00-12:00",
    status: "unavailable",
    alternates: ["12:00-13:00", "15:00-16:00"],
  },
  {
    id: "LAB-2-1000",
    resource: "Lab 2",
    date: "2026-03-02",
    time: "10:00-11:00",
    status: "limited",
    alternates: ["13:00-14:00"],
  },
  {
    id: "CONF-C-1400",
    resource: "Conference C",
    date: "2026-03-02",
    time: "14:00-15:00",
    status: "available",
  },
];

const initialBookingRequests: BookingRequest[] = [
  {
    id: "REQ-1001",
    requester: "Aarav Mehta",
    resource: "Library A",
    date: "2026-03-03",
    time: "10:00-11:00",
    purpose: "Project review meeting",
    participants: 6,
    remarks: "",
    status: "pending",
  },
  {
    id: "REQ-1002",
    requester: "Nisha Verma",
    resource: "Lab 2",
    date: "2026-03-03",
    time: "13:00-14:00",
    purpose: "Robotics practice",
    participants: 12,
    remarks: "",
    status: "pending",
  },
  {
    id: "REQ-1003",
    requester: "Rohan Singh",
    resource: "Conference C",
    date: "2026-03-04",
    time: "15:00-16:00",
    purpose: "Mentorship session",
    participants: 8,
    remarks: "",
    status: "pending",
  },
];

const welcomeMessage: Message = {
  id: "1",
  role: "assistant",
  content: "Hi! Ask policy questions or request a room booking.",
  citations: [
    {
      name: "CampusBookingPolicy_v3.pdf",
      link: "#",
      excerpt:
        "Room booking requests must include purpose, participants, and preferred time slot.",
    },
  ],
};

const initialChatSessions: ChatSession[] = [
  {
    id: "chat-1",
    title: "Campus booking policy guidance",
    updatedAt: "2026-02-28T10:00:00.000Z",
    messages: [
      welcomeMessage,
      {
        id: "2",
        role: "user",
        content: "What details are mandatory to request a room booking?",
      },
      {
        id: "3",
        role: "assistant",
        content:
          "You must include purpose, participant count, and preferred slot. I can help draft that request.",
      },
    ],
  },
  {
    id: "chat-2",
    title: "Lab 2 slot alternatives",
    updatedAt: "2026-02-27T16:45:00.000Z",
    messages: [
      {
        ...welcomeMessage,
        id: "4",
      },
      {
        id: "5",
        role: "user",
        content: "Lab 2 at 10:00 is limited. Suggest alternate slots.",
      },
      {
        id: "6",
        role: "assistant",
        content:
          "Lab 2 has a likely alternate at 13:00-14:00. I can prepare a fallback request for that slot.",
      },
    ],
  },
];

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
  const adminEmails = (process.env.NEXT_PUBLIC_ADMIN_EMAILS ?? "")
    .split(",")
    .map((email) => email.trim().toLowerCase())
    .filter(Boolean);
  const isAdmin = session?.user?.email
    ? adminEmails.includes(session.user.email.toLowerCase())
    : false;

  const [chatSessions, setChatSessions] =
    useState<ChatSession[]>(initialChatSessions);
  const [activeChatId, setActiveChatId] = useState(initialChatSessions[0].id);
  const [bookingRequests, setBookingRequests] = useState<BookingRequest[]>(
    initialBookingRequests,
  );

  const slots = initialSlots;
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [isAvailabilityOpen, setIsAvailabilityOpen] = useState(false);

  const sortedChatSessions = [...chatSessions].sort(
    (left, right) =>
      new Date(right.updatedAt).getTime() - new Date(left.updatedAt).getTime(),
  );

  const activeChat = useMemo(
    () =>
      chatSessions.find((chatSession) => chatSession.id === activeChatId) ??
      chatSessions[0],
    [activeChatId, chatSessions],
  );

  const messages = activeChat?.messages;

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeChat?.id, messages?.length, isLoading]);

  const createNewChat = () => {
    if (isLoading) return;

    const now = new Date().toISOString();
    const newChat: ChatSession = {
      id: `chat-${Date.now()}`,
      title: "New chat",
      updatedAt: now,
      messages: [
        {
          ...welcomeMessage,
          id: `${Date.now()}-welcome`,
        },
      ],
    };

    setChatSessions((previous) => [newChat, ...previous]);
    setActiveChatId(newChat.id);
    setInput("");
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

    setTimeout(() => {
      const botResponse: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content:
          "Mock mode: I can cite docs and propose booking slots once backend is connected.",
        citations: [
          {
            name: "StudentHandbook_2026.md",
            link: "#",
            excerpt:
              "Use approved resources only and submit booking requests at least 2 hours in advance.",
          },
        ],
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
      setIsLoading(false);
    }, 1500);
  };

  const slotStatusColor = (slotStatus: Slot["status"]) => {
    if (slotStatus === "available") return "text-success";
    if (slotStatus === "limited") return "text-pending";
    return "text-danger";
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
    setBookingRequests((previous) =>
      previous.map((request) =>
        request.id === requestId ? { ...request, status: decision } : request,
      ),
    );
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
      <div className="flex min-h-screen flex-col items-center justify-center bg-bg-base px-4 text-center">
        <h1 className="font-display text-3xl font-semibold text-text-primary md:text-4xl">
          CSIS SmartAssist
        </h1>
        <p className="mt-3 max-w-xl text-sm text-text-secondary md:text-base">
          Secure campus assistant with document-grounded responses and smart
          booking requests.
        </p>
        <button
          onClick={() => signIn("google")}
          className="mt-8 border border-accent bg-accent px-6 py-3 text-sm font-medium text-bg-base transition hover:brightness-110"
        >
          Sign in with Google
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-bg-base text-text-primary lg:h-screen lg:overflow-hidden">
      <header className="border-b border-border bg-bg-surface px-4 py-3 md:px-6">
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
        <main className="min-h-[calc(100vh-57px)] px-4 py-4 md:px-6 md:py-6">
          <div className="mb-4 border border-border bg-bg-surface px-4 py-3">
            <h2 className="font-display text-lg font-semibold md:text-xl">
              Booking Requests Dashboard
            </h2>
            <p className="mt-1 text-sm text-text-secondary">
              Review pending requests and add remarks before accepting or
              declining.
            </p>
          </div>

          <div className="ui-scrollbar max-h-[calc(100vh-190px)] space-y-3 overflow-y-auto pr-1">
            {bookingRequests.map((request) => (
              <article
                key={request.id}
                className="border border-border bg-bg-surface p-4"
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
                      Requester:
                    </span>{" "}
                    {request.requester}
                  </p>
                  <p>
                    <span className="font-mono text-text-secondary">
                      Resource:
                    </span>{" "}
                    {request.resource}
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
                      Participants:
                    </span>{" "}
                    {request.participants}
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
        <main className="grid min-h-[calc(100vh-57px)] grid-cols-1 lg:h-[calc(100vh-57px)] lg:min-h-0 lg:grid-cols-12">
          <aside
            id="history-sidebar"
            className={`${isHistoryOpen ? "flex" : "hidden"} min-h-0 flex-col overflow-hidden border-b border-border lg:col-span-3 lg:flex lg:border-b-0 lg:border-r`}
          >
            <div className="flex items-center justify-between border-b border-border bg-bg-surface px-4 py-2 font-mono text-sm text-text-secondary">
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
                        ? "border-accent bg-bg-surface"
                        : "border-border hover:bg-bg-surface"
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

          <section className="flex min-h-[55vh] flex-col border-b border-border lg:col-span-6 lg:min-h-0 lg:overflow-hidden lg:border-b-0 lg:border-r">
            <div className="flex items-center justify-between border-b border-border bg-bg-surface px-4 py-2 font-mono text-sm text-text-secondary md:px-6">
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
                <button
                  onClick={() => setIsAvailabilityOpen((previous) => !previous)}
                  className="border border-border px-2 py-1 text-[11px] text-text-primary transition hover:bg-bg-base"
                  aria-expanded={isAvailabilityOpen}
                  aria-controls="availability-sidebar"
                >
                  {isAvailabilityOpen ? "Hide Info" : "Show Info"}
                </button>
              </div>
            </div>
            <div className="ui-scrollbar lg:min-h-0 lg:flex-1 lg:overflow-y-auto px-4 py-4 md:px-6">
              {messages?.map((message) => (
                <article
                  key={message.id}
                  className="border-b border-border py-4"
                >
                  <p className="font-mono text-xs text-text-secondary md:text-sm">
                    {message.role === "user" ? "You" : "Assistant"}
                  </p>
                  <p className="mt-1 whitespace-pre-wrap text-sm leading-relaxed md:text-base">
                    {message.content}
                  </p>

                  {message.citations && message.citations.length > 0 && (
                    <div className="mt-3 space-y-2 border border-border bg-bg-surface p-3">
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
                </article>
              ))}

              {isLoading && (
                <div className="border-b border-border py-4 font-mono text-sm text-text-secondary">
                  Thinking...
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            <div className="sticky bottom-0 border-t border-border bg-bg-surface px-4 py-3 md:px-6">
              <form onSubmit={handleSendMessage} className="flex gap-2">
                <input
                  type="text"
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  disabled={isLoading}
                  placeholder="Ask about policies, citations, or room booking..."
                  className="h-11 flex-1 border border-border bg-bg-base px-3 text-sm text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-1 focus:ring-link disabled:opacity-60"
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

          <section
            id="availability-sidebar"
            className={`${isAvailabilityOpen ? "flex" : "hidden"} min-h-0 flex-col overflow-hidden lg:col-span-3 lg:flex`}
          >
            <div className="border-b border-border bg-bg-surface px-4 py-2 font-mono text-sm text-text-secondary">
              Availability
            </div>

            <div className="ui-scrollbar min-h-0 flex-1 overflow-y-auto border-b border-border px-4 py-3">
              <p className="mb-2 font-mono text-sm text-text-secondary">
                Current slot availability
              </p>
              <div className="grid grid-cols-[1.3fr_1fr_1fr] gap-1 font-mono text-[11px] sm:text-xs">
                <div className="border border-border bg-bg-surface px-2 py-1 text-text-secondary">
                  RESOURCE
                </div>
                <div className="border border-border bg-bg-surface px-2 py-1 text-text-secondary">
                  TIME
                </div>
                <div className="border border-border bg-bg-surface px-2 py-1 text-text-secondary">
                  STATE
                </div>

                {slots.map((slot) => (
                  <div key={slot.id} className="contents">
                    <span className="border border-border px-2 py-1 text-left text-text-primary">
                      {slot.resource}
                    </span>
                    <span className="border border-border px-2 py-1 text-left text-text-primary">
                      {slot.time}
                    </span>
                    <span
                      className={`border border-border px-2 py-1 text-left uppercase hover:bg-bg-surface ${slotStatusColor(slot.status)}`}
                    >
                      {slot.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </section>
        </main>
      )}
    </div>
  );
}

export default dynamic(() => Promise.resolve(HomePage), { ssr: false });
