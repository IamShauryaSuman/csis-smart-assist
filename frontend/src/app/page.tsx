"use client";

import { useSession, signIn, signOut } from "next-auth/react";

export default function Home() {
  const { data: session, status } = useSession();

  if (status === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center">
        Loading...
      </div>
    );
  }

  // Unauthenticated State: Show Login
  if (!session) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50 p-4">
        <h1 className="mb-6 text-3xl font-bold">CSIS SmartAssist</h1>
        <p className="mb-8 text-gray-600">
          Secure Campus-Wide AI Chatbot & Resource Booking
        </p>
        <button
          onClick={() => signIn("google")}
          className="rounded-md bg-blue-600 px-6 py-3 text-white transition hover:bg-blue-700"
        >
          Sign in with Google
        </button>
      </div>
    );
  }

  // Authenticated State: The Chat UI Skeleton
  return (
    <div className="flex h-screen flex-col bg-white">
      {/* Header */}
      <header className="flex items-center justify-between border-b p-4 shadow-sm">
        <h1 className="text-xl font-semibold">CSIS SmartAssist</h1>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-600">{session.user?.email}</span>
          <button
            onClick={() => signOut()}
            className="text-sm text-red-600 hover:underline"
          >
            Sign out
          </button>
        </div>
      </header>

      {/* Chat History Area (Placeholder) */}
      <main className="flex-1 overflow-y-auto p-4 bg-gray-50">
        <div className="mx-auto max-w-3xl space-y-4">
          <div className="rounded-lg bg-blue-100 p-4 w-fit">
            <p>Hello! I am CSIS SmartAssist. How can I help you today?</p>
          </div>
        </div>
      </main>

      {/* Chat Input Area (Placeholder) */}
      <footer className="border-t p-4">
        <div className="mx-auto max-w-3xl flex gap-2">
          <input
            type="text"
            placeholder="Ask about policies or book a room..."
            className="flex-1 rounded-md border p-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button className="rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700">
            Send
          </button>
        </div>
      </footer>
    </div>
  );
}
