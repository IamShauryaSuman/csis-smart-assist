import { describe, it, expect, vi, beforeEach } from 'vitest';
import { api } from '../lib/api';

// Reset the singleton token state between tests
beforeEach(() => {
  vi.resetAllMocks();
  api.setToken('test-bearer-token');
});

// ── Helper: create a mock fetch response ──────────────────────────────────────

function mockFetchOk(data: unknown) {
  global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => data,
    body: null,
  });
}

function mockFetchError(status: number, detail: string) {
  global.fetch = vi.fn().mockResolvedValue({
    ok: false,
    status,
    json: async () => ({ detail }),
  });
}

// ── Error propagation ─────────────────────────────────────────────────────────

describe('API Client — error handling', () => {
  it('throws error with detail message from API on non-ok response', async () => {
    mockFetchError(400, 'Room not available');
    await expect(api.createBooking({
      room_id: 'dlt_8', room_name: 'DLT-8', title: 'Class',
      start_time: '2026-07-13T11:00:00+05:30', end_time: '2026-07-13T12:00:00+05:30', description: '',
    })).rejects.toThrow('Room not available');
  });

  it('falls back to statusText if json parse fails', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      json: async () => { throw new Error('not json'); },
    });
    await expect(api.listSessions()).rejects.toThrow('Internal Server Error');
  });

  it('attaches Authorization header when token is set', async () => {
    mockFetchOk([]);
    await api.listSessions();
    expect(global.fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: 'Bearer test-bearer-token' }),
      })
    );
  });
});

// ── Chat endpoints ────────────────────────────────────────────────────────────

describe('API Client — chat', () => {
  it('listSessions fetches GET /chat/sessions', async () => {
    const sessions = [{ id: 's-1', title: 'New Chat' }];
    mockFetchOk(sessions);
    const result = await api.listSessions();
    expect(result).toEqual(sessions);
    expect(global.fetch).toHaveBeenCalledWith(expect.stringContaining('/chat/sessions'), expect.any(Object));
  });

  it('createSession posts with title', async () => {
    const session = { id: 's-1', title: 'My Session' };
    mockFetchOk(session);
    const result = await api.createSession('My Session');
    expect(result).toEqual(session);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/chat/sessions'),
      expect.objectContaining({ method: 'POST', body: JSON.stringify({ title: 'My Session' }) })
    );
  });

  it('createSession uses "New Chat" default title', async () => {
    mockFetchOk({});
    await api.createSession();
    expect(global.fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({ body: JSON.stringify({ title: 'New Chat' }) })
    );
  });

  it('deleteSession sends DELETE request', async () => {
    mockFetchOk({});
    await api.deleteSession('s-123');
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/chat/sessions/s-123'),
      expect.objectContaining({ method: 'DELETE' })
    );
  });

  it('updateSession sends PATCH with updates', async () => {
    const updated = { id: 's-1', title: 'Renamed' };
    mockFetchOk(updated);
    const result = await api.updateSession('s-1', { title: 'Renamed' });
    expect(result).toEqual(updated);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/chat/sessions/s-1'),
      expect.objectContaining({ method: 'PATCH', body: JSON.stringify({ title: 'Renamed' }) })
    );
  });

  it('getSessionMessages fetches messages for a session', async () => {
    const messages = [{ id: 'm-1', role: 'user', content: 'Hi' }];
    mockFetchOk(messages);
    const result = await api.getSessionMessages('s-123');
    expect(result).toEqual(messages);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/chat/sessions/s-123/messages'),
      expect.any(Object)
    );
  });
});

// ── Booking endpoints ─────────────────────────────────────────────────────────

describe('API Client — bookings', () => {
  it('createBooking posts to correct endpoint and returns data', async () => {
    const mockResponse = { id: 'b-123', status: 'pending' };
    mockFetchOk(mockResponse);
    const payload = {
      room_id: 'dlt_8', room_name: 'DLT-8', title: 'Class',
      start_time: '2026-07-13T11:00:00+05:30', end_time: '2026-07-13T12:00:00+05:30', description: '',
    };
    const result = await api.createBooking(payload);
    expect(result).toEqual(mockResponse);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/bookings'),
      expect.objectContaining({ method: 'POST', body: JSON.stringify(payload) })
    );
  });

  it('listBookings with no options fetches plain /bookings', async () => {
    mockFetchOk([]);
    await api.listBookings();
    expect(global.fetch).toHaveBeenCalledWith(expect.stringMatching(/\/bookings$/), expect.any(Object));
  });

  it('listBookings with status filter appends query param', async () => {
    mockFetchOk([]);
    await api.listBookings({ status: 'pending' });
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('status=pending'), expect.any(Object)
    );
  });

  it('listBookings with allUsers appends all_users=true', async () => {
    mockFetchOk([]);
    await api.listBookings({ allUsers: true });
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('all_users=true'), expect.any(Object)
    );
  });

  it('updateBookingStatus sends PATCH to /bookings/:id/status', async () => {
    const updated = { id: 'b-1', status: 'approved' };
    mockFetchOk(updated);
    const result = await api.updateBookingStatus('b-1', 'approved', 'Looks good');
    expect(result).toEqual(updated);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/bookings/b-1/status'),
      expect.objectContaining({
        method: 'PATCH',
        body: JSON.stringify({ status: 'approved', admin_notes: 'Looks good' }),
      })
    );
  });

  it('lockBooking sends POST to /bookings/:id/lock', async () => {
    mockFetchOk({ id: 'b-1', is_locked: true });
    await api.lockBooking('b-1');
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/bookings/b-1/lock'),
      expect.objectContaining({ method: 'POST' })
    );
  });

  it('unlockBooking sends POST to /bookings/:id/unlock', async () => {
    mockFetchOk({ id: 'b-1', is_locked: false });
    await api.unlockBooking('b-1');
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/bookings/b-1/unlock'),
      expect.objectContaining({ method: 'POST' })
    );
  });

  it('updateBookingDetails sends PATCH to /bookings/:id', async () => {
    const updated = { id: 'b-1', title: 'Updated Title' };
    mockFetchOk(updated);
    const data = {
      room_id: 'dlt_8', room_name: 'DLT-8', title: 'Updated Title',
      start_time: '2026-07-14T10:00:00Z', end_time: '2026-07-14T11:00:00Z',
    };
    const result = await api.updateBookingDetails('b-1', data);
    expect(result).toEqual(updated);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/bookings/b-1'),
      expect.objectContaining({ method: 'PATCH', body: JSON.stringify(data) })
    );
  });
});

// ── SSE streaming ─────────────────────────────────────────────────────────────

describe('API Client — sendMessageStream', () => {
  function makeSseStream(events: object[]) {
    const lines = events
      .map(e => `data: ${JSON.stringify(e)}\n\n`)
      .join('');
    const encoder = new TextEncoder();
    const chunks = [encoder.encode(lines)];
    let idx = 0;
    const reader = {
      read: vi.fn().mockImplementation(async () => {
        if (idx < chunks.length) return { done: false, value: chunks[idx++] };
        return { done: true, value: undefined };
      }),
    };
    return { getReader: () => reader };
  }

  it('calls onMetadata with metadata event', async () => {
    const onMetadata = vi.fn();
    const onChunk = vi.fn();
    const onError = vi.fn();

    const meta = { type: 'metadata', intent: 'general_query', confidence: 0.9 };
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      body: makeSseStream([meta]),
    });

    await api.sendMessageStream('s-1', 'Hello', onMetadata, onChunk, onError);
    expect(onMetadata).toHaveBeenCalledWith(meta);
    expect(onError).not.toHaveBeenCalled();
  });

  it('calls onChunk for each chunk event', async () => {
    const onMetadata = vi.fn();
    const onChunk = vi.fn();
    const onError = vi.fn();

    const events = [
      { type: 'metadata', intent: 'general_query', confidence: 0.9 },
      { type: 'chunk', text: 'Hello ' },
      { type: 'chunk', text: 'World' },
      { type: 'done' },
    ];
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      body: makeSseStream(events),
    });

    await api.sendMessageStream('s-1', 'Hi', onMetadata, onChunk, onError);
    expect(onChunk).toHaveBeenCalledTimes(2);
    expect(onChunk).toHaveBeenCalledWith('Hello ');
    expect(onChunk).toHaveBeenCalledWith('World');
  });

  it('calls onError for error event from SSE stream', async () => {
    const onMetadata = vi.fn();
    const onChunk = vi.fn();
    const onError = vi.fn();

    const events = [{ type: 'error', detail: 'LLM Rate limit exceeded' }];
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      body: makeSseStream(events),
    });

    await api.sendMessageStream('s-1', 'Hi', onMetadata, onChunk, onError);
    expect(onError).toHaveBeenCalledWith(expect.objectContaining({ message: 'LLM Rate limit exceeded' }));
  });

  it('calls onError if fetch itself fails', async () => {
    const onError = vi.fn();
    global.fetch = vi.fn().mockRejectedValue(new Error('Network error'));

    await api.sendMessageStream('s-1', 'Hi', vi.fn(), vi.fn(), onError);
    expect(onError).toHaveBeenCalledWith(expect.objectContaining({ message: 'Network error' }));
  });

  it('calls onError if response is not ok', async () => {
    const onError = vi.fn();
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 429,
      json: async () => ({ detail: 'Rate limit exceeded' }),
    });

    await api.sendMessageStream('s-1', 'Hi', vi.fn(), vi.fn(), onError);
    expect(onError).toHaveBeenCalledWith(expect.objectContaining({ message: 'Rate limit exceeded' }));
  });
});
