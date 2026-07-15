import { renderHook, act, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// ── Use vi.hoisted to avoid TDZ issues with vi.mock hoisting ──────────────────

const { 
  mockSetToken, 
  mockGetSession, 
  mockOnAuthStateChange, 
  mockSignOut, 
  mockSignInWithIdToken, 
  mockUnsubscribe,
  mockSupabase 
} = vi.hoisted(() => {
  const mockGetSession = vi.fn();
  const mockOnAuthStateChange = vi.fn();
  const mockSignOut = vi.fn();
  const mockSignInWithIdToken = vi.fn();

  return {
    mockSetToken: vi.fn(),
    mockGetSession,
    mockOnAuthStateChange,
    mockSignOut,
    mockSignInWithIdToken,
    mockUnsubscribe: vi.fn(),
    mockSupabase: {
      auth: {
        getSession: mockGetSession,
        onAuthStateChange: mockOnAuthStateChange,
        signOut: mockSignOut,
        signInWithIdToken: mockSignInWithIdToken,
      },
    },
  };
});

vi.mock('../lib/api', () => ({
  api: { setToken: mockSetToken },
}));

vi.mock('../lib/supabase/client', () => ({
  createClient: () => mockSupabase,
}));

import { useAuth } from '../lib/hooks/useAuth';

const mockUser = { id: 'u-123', email: 'test@goa.bits-pilani.ac.in' };

// Holds the registered onAuthStateChange callback so tests can call it manually
let capturedAuthCallback: ((event: string, session: any) => void) | undefined;

describe('useAuth', () => {
  beforeEach(() => {
    mockSetToken.mockReset();
    mockSignOut.mockReset();
    mockSignInWithIdToken.mockReset();
    capturedAuthCallback = undefined;

    mockGetSession.mockResolvedValue({
      data: { session: { user: mockUser, access_token: 'mock-token' } },
    });
    // Capture the callback when the hook registers it
    mockOnAuthStateChange.mockImplementation((cb: (event: string, session: any) => void) => {
      capturedAuthCallback = cb;
      return { data: { subscription: { unsubscribe: mockUnsubscribe } } };
    });
    mockSignOut.mockResolvedValue({ error: null });
    mockSignInWithIdToken.mockResolvedValue({ error: null });
  });


  it('initializes with user=null and loading=true', () => {
    const { result } = renderHook(() => useAuth());
    expect(result.current.loading).toBe(true);
    expect(result.current.user).toBeNull();
  });

  it('loads user from existing Supabase session', async () => {
    const { result } = renderHook(() => useAuth());

    await act(async () => {
      await new Promise(r => setTimeout(r, 10));
    });

    expect(result.current.user).toEqual(mockUser);
    expect(result.current.loading).toBe(false);
    expect(mockSetToken).toHaveBeenCalledWith('mock-token');
  });

  it('remains user=null if no active session exists', async () => {
    mockGetSession.mockResolvedValue({ data: { session: null } });
    const { result } = renderHook(() => useAuth());

    await act(async () => {
      await new Promise(r => setTimeout(r, 10));
    });

    expect(result.current.user).toBeNull();
    expect(result.current.loading).toBe(false);
  });

  it('signOut clears the user and resets API token', async () => {
    const { result } = renderHook(() => useAuth());
    await act(async () => { await new Promise(r => setTimeout(r, 10)); });

    expect(result.current.user).toEqual(mockUser);

    await act(async () => { await result.current.signOut(); });

    // Simulate the auth state change that supabase fires after signOut
    await act(async () => { capturedAuthCallback?.('SIGNED_OUT', null); });

    expect(mockSignOut).toHaveBeenCalled();
    expect(result.current.user).toBeNull();
    expect(mockSetToken).toHaveBeenCalledWith('');
  });

  it('signInWithIdToken calls supabase signInWithIdToken with google provider', async () => {
    const { result } = renderHook(() => useAuth());
    
    // Wait for initial load to finish
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    await act(async () => { await result.current.signInWithIdToken("test-token"); });

    expect(mockSignInWithIdToken).toHaveBeenCalledWith({
      provider: 'google',
      token: "test-token",
    });
  });

  it('updates user when auth state changes to SIGNED_IN', async () => {
    renderHook(() => useAuth());

    // capturedAuthCallback is set synchronously during mount
    expect(capturedAuthCallback).toBeDefined();

    await act(async () => {
      capturedAuthCallback!('SIGNED_IN', {
        user: { id: 'u-456', email: 'other@bits.ac.in' },
        access_token: 'new-token',
      });
    });

    expect(mockSetToken).toHaveBeenCalledWith('new-token');
  });

  it('clears user on SIGNED_OUT event', async () => {
    const { result } = renderHook(() => useAuth());
    await act(async () => { await new Promise(r => setTimeout(r, 10)); });

    // User should be loaded
    expect(result.current.user).toEqual(mockUser);

    await act(async () => { capturedAuthCallback?.('SIGNED_OUT', null); });

    expect(result.current.user).toBeNull();
  });
});
