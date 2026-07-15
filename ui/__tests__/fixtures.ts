import { vi } from 'vitest';
import type { Booking, ChatSession, Message, Profile } from '@/lib/types';

// ── Booking Fixtures ─────────────────────────────────────────────────────────

export const mockBooking: Booking = {
  id: 'b-123',
  user_id: 'u-123',
  room_id: 'dlt_8',
  room_name: 'DLT-8',
  title: 'CS F111 Lecture',
  description: 'Regular class',
  start_time: '2026-07-13T11:00:00+05:30',
  end_time: '2026-07-13T12:00:00+05:30',
  status: 'pending',
  admin_notes: '',
  is_locked: false,
  locked_by: null,
  locked_at: null,
  created_at: '2026-07-13T09:00:00Z',
  updated_at: '2026-07-13T09:00:00Z',
};

export const mockApprovedBooking: Booking = {
  ...mockBooking,
  id: 'b-456',
  status: 'approved',
  admin_notes: 'Approved. Have a great class!',
};

export const mockRejectedBooking: Booking = {
  ...mockBooking,
  id: 'b-789',
  status: 'rejected',
  admin_notes: 'Conflicts with another booking.',
};

// ── Chat Fixtures ─────────────────────────────────────────────────────────────

export const mockSession: ChatSession = {
  id: 's-123',
  user_id: 'u-123',
  title: 'New Chat',
  is_pinned: false,
  created_at: '2026-07-13T09:00:00Z',
  updated_at: '2026-07-13T09:00:00Z',
};

export const mockUserMessage: Message = {
  id: 'm-1',
  session_id: 's-123',
  role: 'user',
  content: 'Hello, how do I book a room?',
  interactive_type: null,
  interactive_payload: null,
  created_at: '2026-07-13T09:01:00Z',
};

export const mockAssistantMessage: Message = {
  id: 'm-2',
  session_id: 's-123',
  role: 'assistant',
  content: 'Sure! I can help you book a room. Which lab do you need?',
  interactive_type: null,
  interactive_payload: null,
  created_at: '2026-07-13T09:01:05Z',
};

export const mockProposalMessage: Message = {
  id: 'm-3',
  session_id: 's-123',
  role: 'assistant',
  content: 'Here is a booking proposal for DLT-8.',
  interactive_type: 'booking_proposal',
  interactive_payload: {
    room_id: 'dlt_8',
    room_name: 'DLT-8',
    title: 'CS F111 Lecture',
    start_time: '2026-07-13T11:00:00+05:30',
    end_time: '2026-07-13T12:00:00+05:30',
    description: 'Regular class',
  },
  created_at: '2026-07-13T09:02:00Z',
};

// ── Profile Fixtures ──────────────────────────────────────────────────────────

export const mockProfile: Profile = {
  id: 'u-123',
  email: 'test@goa.bits-pilani.ac.in',
  full_name: 'Test User',
  academic_role: 'undergraduate',
  department: 'Computer Science',
  year: 3,
  interests: ['AI', 'Web Dev'],
  synthesized_memory: '',
  is_admin: false,
  created_at: '2026-07-01T00:00:00Z',
  updated_at: '2026-07-13T09:00:00Z',
};

// ── Mock Supabase Client ──────────────────────────────────────────────────────

export const mockSupabaseClient = {
  channel: vi.fn().mockReturnValue({
    on: vi.fn().mockReturnThis(),
    subscribe: vi.fn().mockReturnThis(),
  }),
  removeChannel: vi.fn(),
  auth: {
    getUser: vi.fn().mockResolvedValue({ data: { user: { id: 'u-123' } }, error: null }),
    getSession: vi.fn().mockResolvedValue({ 
      data: { session: { user: { id: 'u-123', email: 'test@goa.bits-pilani.ac.in' }, access_token: 'mock-token' } },
      error: null 
    }),
    onAuthStateChange: vi.fn().mockReturnValue({ data: { subscription: { unsubscribe: vi.fn() } } }),
    signOut: vi.fn().mockResolvedValue({ error: null }),
    signInWithOAuth: vi.fn().mockResolvedValue({ error: null }),
  },
  from: vi.fn().mockReturnValue({
    select: vi.fn().mockReturnThis(),
    eq: vi.fn().mockReturnThis(),
    single: vi.fn().mockResolvedValue({ data: mockProfile, error: null }),
    upsert: vi.fn().mockReturnThis(),
    update: vi.fn().mockReturnThis(),
  }),
};

// ── Mock API ──────────────────────────────────────────────────────────────────

export const mockApi = {
  listBookings: vi.fn().mockResolvedValue([mockBooking]),
  createBooking: vi.fn().mockResolvedValue(mockBooking),
  updateBookingStatus: vi.fn().mockResolvedValue({ ...mockBooking, status: 'approved' }),
  lockBooking: vi.fn().mockResolvedValue({ ...mockBooking, is_locked: true }),
  unlockBooking: vi.fn().mockResolvedValue({ ...mockBooking, is_locked: false }),
  updateBookingDetails: vi.fn().mockResolvedValue({ ...mockBooking, title: 'Updated Title' }),
  listSessions: vi.fn().mockResolvedValue([mockSession]),
  createSession: vi.fn().mockResolvedValue(mockSession),
  deleteSession: vi.fn().mockResolvedValue(undefined),
  updateSession: vi.fn().mockResolvedValue({ ...mockSession, title: 'Renamed Chat' }),
  getSessionMessages: vi.fn().mockResolvedValue([mockUserMessage, mockAssistantMessage]),
  setToken: vi.fn(),
};
