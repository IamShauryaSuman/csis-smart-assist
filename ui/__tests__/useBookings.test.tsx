import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// ── Use vi.hoisted to avoid TDZ issues with vi.mock hoisting ──────────────────

const {
  mockListBookings,
  mockCreateBookingApi,
  mockUpdateBookingStatus,
  mockLockBooking,
  mockUnlockBooking,
  mockUpdateBookingDetails,
  mockChannel,
  mockRemoveChannel,
} = vi.hoisted(() => {
  const mockChannel = {
    on: vi.fn().mockReturnThis(),
    subscribe: vi.fn().mockReturnThis(),
  };
  return {
    mockListBookings: vi.fn(),
    mockCreateBookingApi: vi.fn(),
    mockUpdateBookingStatus: vi.fn(),
    mockLockBooking: vi.fn(),
    mockUnlockBooking: vi.fn(),
    mockUpdateBookingDetails: vi.fn(),
    mockChannel,
    mockRemoveChannel: vi.fn(),
  };
});

vi.mock('../lib/api', () => ({
  api: {
    listBookings: mockListBookings,
    createBooking: mockCreateBookingApi,
    updateBookingStatus: mockUpdateBookingStatus,
    lockBooking: mockLockBooking,
    unlockBooking: mockUnlockBooking,
    updateBookingDetails: mockUpdateBookingDetails,
    setToken: vi.fn(),
  },
}));

vi.mock('../lib/supabase/client', () => ({
  createClient: () => ({
    channel: vi.fn(() => mockChannel),
    removeChannel: mockRemoveChannel,
  }),
}));

import { mockBooking, mockApprovedBooking } from './fixtures';
import { useBookings } from '../lib/hooks/useBookings';

describe('useBookings', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListBookings.mockResolvedValue([mockBooking]);
    mockCreateBookingApi.mockResolvedValue(mockBooking);
    mockUpdateBookingStatus.mockResolvedValue(mockApprovedBooking);
    mockLockBooking.mockResolvedValue({ ...mockBooking, is_locked: true });
    mockUnlockBooking.mockResolvedValue({ ...mockBooking, is_locked: false });
    mockUpdateBookingDetails.mockResolvedValue({ ...mockBooking, title: 'Updated Title' });
    mockChannel.on.mockReturnThis();
    mockChannel.subscribe.mockReturnThis();
  });

  it('initializes with empty bookings and not loading', () => {
    const { result } = renderHook(() => useBookings('u-123'));
    expect(result.current.bookings).toEqual([]);
    expect(result.current.loading).toBe(false);
  });

  it('loadBookings populates bookings from API', async () => {
    const { result } = renderHook(() => useBookings('u-123'));

    await act(async () => {
      await result.current.loadBookings();
    });

    expect(mockListBookings).toHaveBeenCalledWith({});
    expect(result.current.bookings).toEqual([mockBooking]);
  });

  it('loadBookings sets loading to true then false', async () => {
    const { result } = renderHook(() => useBookings('u-123'));

    let resolve: (v: unknown) => void;
    mockListBookings.mockReturnValueOnce(new Promise(r => { resolve = r; }));

    act(() => { result.current.loadBookings(); });
    expect(result.current.loading).toBe(true);

    await act(async () => { resolve!([mockBooking]); });
    expect(result.current.loading).toBe(false);
  });

  it('createBooking appends new booking to state', async () => {
    const { result } = renderHook(() => useBookings('u-123'));
    await act(async () => { await result.current.loadBookings(); });

    const newBooking = { ...mockBooking, id: 'b-new', title: 'New Booking' };
    mockCreateBookingApi.mockResolvedValueOnce(newBooking);

    await act(async () => {
      await result.current.createBooking({
        room_id: 'dlt_8', room_name: 'DLT-8', title: 'New Booking',
        start_time: '2026-07-14T10:00:00Z', end_time: '2026-07-14T11:00:00Z',
      });
    });

    expect(result.current.bookings).toHaveLength(2);
    expect(result.current.bookings[0].id).toBe('b-new');
  });

  it('createBooking propagates API errors', async () => {
    mockCreateBookingApi.mockRejectedValueOnce(new Error('Room not available'));
    const { result } = renderHook(() => useBookings('u-123'));

    await expect(
      act(async () => {
        await result.current.createBooking({ room_id: 'x', room_name: 'X', title: 'T', start_time: '', end_time: '' });
      })
    ).rejects.toThrow('Room not available');
  });

  it('updateBookingStatus replaces the matching booking in state', async () => {
    const { result } = renderHook(() => useBookings('u-123'));
    await act(async () => { await result.current.loadBookings(); });

    await act(async () => {
      await result.current.updateBookingStatus('b-123', 'approved', 'Looks good');
    });

    expect(result.current.bookings[0].status).toBe('approved');
    expect(result.current.bookings[0].admin_notes).toBe('Approved. Have a great class!');
  });

  it('lockBooking updates is_locked on the matching booking', async () => {
    const { result } = renderHook(() => useBookings('u-123'));
    await act(async () => { await result.current.loadBookings(); });

    await act(async () => { await result.current.lockBooking('b-123'); });
    expect(result.current.bookings[0].is_locked).toBe(true);
  });

  it('unlockBooking clears is_locked on the matching booking', async () => {
    mockListBookings.mockResolvedValueOnce([{ ...mockBooking, is_locked: true }]);
    const { result } = renderHook(() => useBookings('u-123'));
    await act(async () => { await result.current.loadBookings(); });

    await act(async () => { await result.current.unlockBooking('b-123'); });
    expect(result.current.bookings[0].is_locked).toBe(false);
  });

  it('updateBookingDetails updates the matching booking in state', async () => {
    const { result } = renderHook(() => useBookings('u-123'));
    await act(async () => { await result.current.loadBookings(); });

    await act(async () => {
      await result.current.updateBookingDetails('b-123', {
        room_id: 'dlt_8', room_name: 'DLT-8', title: 'Updated Title',
        start_time: '2026-07-14T10:00:00Z', end_time: '2026-07-14T11:00:00Z',
      });
    });

    expect(result.current.bookings[0].title).toBe('Updated Title');
  });

  it('subscribes to supabase realtime channel for the user', () => {
    renderHook(() => useBookings('u-123'));
    expect(mockChannel.on).toHaveBeenCalled();
    expect(mockChannel.subscribe).toHaveBeenCalled();
  });

  it('does not subscribe when userId is undefined', () => {
    renderHook(() => useBookings(undefined));
    expect(mockChannel.subscribe).not.toHaveBeenCalled();
  });
});
