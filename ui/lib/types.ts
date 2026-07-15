/**
 * CSIS SmartAssist — Global TypeScript Type Definitions
 *
 * Single source of truth for all data models shared across the frontend.
 * Maps directly to the Supabase database schema.
 */

// ── Database Models ────────────────────────────────────────────────────────

export interface Profile {
  id: string;
  email: string;
  full_name: string | null;
  academic_role: "undergraduate" | "higher_degree" | "faculty" | null;
  department: string | null;
  year: number | null;
  interests: string[];
  synthesized_memory: string;
  is_admin: boolean;
  created_at: string;
  updated_at: string;
}

export interface ChatSession {
  id: string;
  user_id: string;
  title: string;
  is_pinned?: boolean;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  session_id: string;
  role: "user" | "assistant";
  content: string;
  interactive_type: string | null;
  interactive_payload: Record<string, unknown> | null;
  created_at: string;
}

export interface Booking {
  id: string;
  user_id: string;
  room_id: string;
  room_name: string;
  title: string;
  description: string | null;
  start_time: string;
  end_time: string;
  status: "pending" | "approved" | "rejected" | "expired";
  admin_notes: string | null;
  is_locked?: boolean;
  locked_by?: string | null;
  locked_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface RagFile {
  id: string;
  gdrive_id: string;
  name: string;
  mime_type: string;
  md5_checksum: string;
  updated_at: string;
}

// ── API Response Types ─────────────────────────────────────────────────────

export interface FileDelta {
  gdrive_id: string;
  name: string;
  mime_type: string;
  md5_checksum: string;
  operation: "new" | "modified" | "deleted";
}

export interface DeltaResponse {
  new: FileDelta[];
  modified: FileDelta[];
  deleted: FileDelta[];
  total_changes: number;
}

export interface SyncResult {
  file_id: string;
  gdrive_id: string;
  name: string;
  chunks_created: number;
  status: string;
}

export interface RagStats {
  total_files: number;
  total_chunks: number;
  files: Array<{
    id: string;
    name: string;
    mime_type: string;
    updated_at: string;
    chunk_count: number;
  }>;
}

export interface ChatResponse {
  assistant_message: Message;
  intent: string;
  confidence: number;
  session_title?: string;
}

// ── Room Types ─────────────────────────────────────────────────────────────

export interface Room {
  id: string;
  name: string;
  type: string;
  capacity: number;
  hardware: string[];
  calendar_id: string;
  description: string;
}

export interface BookingProposalPayload {
  room_id: string;
  room_name: string;
  title: string;
  start_time: string;
  end_time: string;
  description?: string;
}

// ── Onboarding Types ───────────────────────────────────────────────────────

export interface OnboardingFormData {
  full_name: string;
  academic_role: "undergraduate" | "higher_degree" | "faculty";
  department: string;
  year: number | null;
  interests: string[];
}

// ── UI State Types ─────────────────────────────────────────────────────────

export type LoadingState = "idle" | "loading" | "error" | "success";
