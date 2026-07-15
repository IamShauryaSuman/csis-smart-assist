/**
 * useAuth — Authentication state hook.
 *
 * Manages Supabase auth state, Google OAuth sign-in/out,
 * and synchronizes the API client token.
 */

"use client";

import { useCallback, useEffect, useState } from "react";
import type { User } from "@supabase/supabase-js";
import { createClient } from "@/lib/supabase/client";
import { api } from "@/lib/api";

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const supabase = createClient();

  useEffect(() => {
    // Get initial session
    const initAuth = async () => {
      try {
        const {
          data: { session },
        } = await supabase.auth.getSession();

        if (session) {
          setUser(session.user);
          api.setToken(session.access_token);
        }
      } finally {
        setLoading(false);
      }
    };

    initAuth();

    // Listen for auth state changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
      if (session) {
        api.setToken(session.access_token);
      }
      setLoading(false);
    });

    return () => subscription.unsubscribe();
  }, [supabase.auth]);

  const signInWithGoogle = useCallback(async () => {
    const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
    const redirectUri = `${window.location.origin}/auth-callback`;
    
    if (!clientId) {
      console.error("Missing NEXT_PUBLIC_GOOGLE_CLIENT_ID");
      return;
    }

    // Generate a secure raw nonce
    const rawNonce = crypto.randomUUID().replace(/-/g, '') + crypto.randomUUID().replace(/-/g, '');
    
    // Hash it with SHA-256 for Google
    const encoder = new TextEncoder();
    const encodedNonce = encoder.encode(rawNonce);
    const hashBuffer = await crypto.subtle.digest('SHA-256', encodedNonce);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    const hashedNonce = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');

    // Store raw nonce in localStorage for Supabase verification
    if (typeof window !== "undefined") {
      localStorage.setItem("supabase-auth-nonce", rawNonce);
    }
    
    const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${clientId}&redirect_uri=${encodeURIComponent(redirectUri)}&response_type=id_token&scope=openid%20email%20profile&prompt=select_account&nonce=${hashedNonce}`;
    
    window.location.href = authUrl;
  }, []);

  const signInWithIdToken = useCallback(async (token: string, nonce?: string) => {
    setLoading(true);
    const { error } = await supabase.auth.signInWithIdToken({
      provider: "google",
      token,
      nonce,
    });
    if (error) {
      setLoading(false);
      console.error("Sign-in error:", error.message);
      throw error;
    }
    // Loading stays true until onAuthStateChange picks up the session
  }, [supabase.auth]);

  const signOut = useCallback(async () => {
    await supabase.auth.signOut();
    setUser(null);
    api.setToken("");
  }, [supabase.auth]);

  return { user, loading, signInWithGoogle, signInWithIdToken, signOut };
}
