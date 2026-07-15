/**
 * Backend API client — handles all communication with the FastAPI backend.
 *
 * Every request includes the Supabase access token for authentication.
 * The backend validates tokens via the Supabase admin client.
 */

import type {
  Booking,
  ChatResponse,
  ChatSession,
  DeltaResponse,
  Message,
  RagStats,
  Room,
  SyncResult,
} from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class APIClient {
  private token: string = "";

  setToken(token: string): void {
    this.token = token;
  }

  private async request<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE}/api${path}`;
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    };

    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        detail: response.statusText,
      }));
      throw new Error(error.detail || `API error: ${response.status}`);
    }

    return response.json();
  }

  // ── Chat Endpoints ─────────────────────────────────────────────────────

  /**
   * Fetch all chat sessions for the authenticated user.
   */
  async listSessions(): Promise<ChatSession[]> {
    return this.request<ChatSession[]>("/chat/sessions");
  }

  async createSession(title?: string): Promise<ChatSession> {
    return this.request<ChatSession>("/chat/sessions", {
      method: "POST",
      body: JSON.stringify({ title: title || "New Chat" }),
    });
  }

  async getSessionMessages(sessionId: string): Promise<Message[]> {
    return this.request<Message[]>(`/chat/sessions/${sessionId}/messages`);
  }

  async deleteSession(sessionId: string): Promise<void> {
    await this.request(`/chat/sessions/${sessionId}`, { method: "DELETE" });
  }

  async updateSession(
    sessionId: string,
    updates: { title?: string; is_pinned?: boolean }
  ): Promise<ChatSession> {
    return this.request<ChatSession>(`/chat/sessions/${sessionId}`, {
      method: "PATCH",
      body: JSON.stringify(updates),
    });
  }

  /**
   * Stream a chat response from the backend.
   * Uses Server-Sent Events (SSE) to yield metadata, chunks, and errors.
   */
  async sendMessageStream(
    sessionId: string,
    message: string,
    onMetadata: (meta: any) => void,
    onChunk: (text: string) => void,
    onError: (err: any) => void
  ): Promise<void> {
    const url = `${API_BASE}/api/chat/send`;
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }

    try {
      const response = await fetch(url, {
        method: "POST",
        headers,
        body: JSON.stringify({ session_id: sessionId, message }),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({
          detail: response.statusText,
        }));
        throw new Error(error.detail || `API error: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder("utf-8");

      if (!reader) throw new Error("No readable stream");

      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        
        // Process lines (SSE format: data: {...}\n\n)
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || ""; // Keep the last incomplete block in buffer

        for (const block of lines) {
          if (block.startsWith("data: ")) {
            const dataStr = block.substring(6).trim();
            if (!dataStr) continue;
            
            try {
              const data = JSON.parse(dataStr);
              if (data.type === "metadata") {
                onMetadata(data);
              } else if (data.type === "chunk") {
                onChunk(data.text);
              } else if (data.type === "error") {
                onError(new Error(data.detail));
              } else if (data.type === "done") {
                // Finished stream
              }
            } catch (e) {
              console.error("Failed to parse SSE JSON:", e, "Data string:", dataStr);
            }
          }
        }
      }
    } catch (error) {
      onError(error);
    }
  }

  async synthesizeMemory(sessionId: string): Promise<void> {
    await this.request(`/chat/sessions/${sessionId}/synthesize`, {
      method: "POST",
    });
  }

  // ── Booking Endpoints ──────────────────────────────────────────────────

  /**
   * Retrieve bookings with optional filtering.
   * If `allUsers` is true, requires admin privileges on the backend.
   */
  async listBookings(
    options: { status?: string; allUsers?: boolean } = {}
  ): Promise<Booking[]> {
    const params = new URLSearchParams();
    if (options.status) params.set("status", options.status);
    if (options.allUsers) params.set("all_users", "true");
    const query = params.toString();
    return this.request<Booking[]>(`/bookings${query ? `?${query}` : ""}`);
  }

  async createBooking(data: {
    room_id: string;
    room_name: string;
    title: string;
    description?: string;
    start_time: string;
    end_time: string;
  }): Promise<Booking> {
    return this.request<Booking>("/bookings", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async updateBookingStatus(
    bookingId: string,
    status: "approved" | "rejected",
    adminNotes?: string
  ): Promise<Booking> {
    return this.request<Booking>(`/bookings/${bookingId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status, admin_notes: adminNotes || "" }),
    });
  }

  async lockBooking(bookingId: string): Promise<Booking> {
    return this.request<Booking>(`/bookings/${bookingId}/lock`, {
      method: "POST",
    });
  }

  async unlockBooking(bookingId: string): Promise<Booking> {
    return this.request<Booking>(`/bookings/${bookingId}/unlock`, {
      method: "POST",
    });
  }

  async updateBookingDetails(
    bookingId: string,
    data: {
      room_id: string;
      room_name: string;
      title: string;
      description?: string;
      start_time: string;
      end_time: string;
    }
  ): Promise<Booking> {
    return this.request<Booking>(`/bookings/${bookingId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }

  async listRooms(): Promise<Room[]> {
    return this.request<Room[]>("/bookings/rooms/list");
  }

  // ── RAG Endpoints ──────────────────────────────────────────────────────

  /**
   * Compare Google Drive state against Supabase pgvector state to identify
   * new, modified, or deleted files.
   */
  async getRagDelta(): Promise<DeltaResponse> {
    return this.request<DeltaResponse>("/rag/delta");
  }

  async syncFile(gdriveId: string): Promise<SyncResult> {
    return this.request<SyncResult>(
      `/rag/sync-file?gdrive_id=${encodeURIComponent(gdriveId)}`,
      { method: "POST" }
    );
  }

  async deleteRagFile(gdriveId: string): Promise<void> {
    await this.request(
      `/rag/file?gdrive_id=${encodeURIComponent(gdriveId)}`,
      { method: "DELETE" }
    );
  }

  async getRagStats(): Promise<RagStats> {
    return this.request<RagStats>("/rag/stats");
  }
}

// Singleton instance
export const api = new APIClient();
