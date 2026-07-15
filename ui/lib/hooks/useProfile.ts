/**
 * useProfile — Profile state management hook.
 *
 * Handles profile loading, creation (onboarding), and updates.
 * Detects whether the user needs onboarding.
 */

"use client";

import { useCallback, useEffect, useState, useMemo } from "react";
import { createClient } from "@/lib/supabase/client";
import type { OnboardingFormData, Profile } from "@/lib/types";

export function useProfile(userId: string | undefined) {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [needsOnboarding, setNeedsOnboarding] = useState(false);
  const supabase = useMemo(() => createClient(), []);

  useEffect(() => {
    if (!userId) {
      setLoading(false);
      return;
    }

    const loadProfile = async () => {
      setLoading(true);
      try {
        const { data, error } = await supabase
          .from("profiles")
          .select("*")
          .eq("id", userId)
          .single();

        if (error || !data) {
          setNeedsOnboarding(true);
          setProfile(null);
        } else if (!data.academic_role) {
          // Profile exists but onboarding incomplete
          setNeedsOnboarding(true);
          setProfile(data as Profile);
        } else {
          setProfile(data as Profile);
          setNeedsOnboarding(false);
        }
      } catch {
        setNeedsOnboarding(true);
      } finally {
        setLoading(false);
      }
    };

    loadProfile();
  }, [userId, supabase]);

  const createProfile = useCallback(
    async (formData: OnboardingFormData) => {
      if (!userId) throw new Error("No user ID");

      const { data: userData } = await supabase.auth.getUser();
      const email = userData.user?.email || "";

      const profileData = {
        id: userId,
        email,
        full_name: formData.full_name,
        academic_role: formData.academic_role,
        department: formData.department,
        year: formData.year,
        interests: formData.interests,
        synthesized_memory: "",
        is_admin: false,
      };

      const { data, error } = await supabase
        .from("profiles")
        .upsert(profileData, { onConflict: 'id' })
        .select()
        .single();

      if (error) throw error;
      setProfile(data as Profile);
      setNeedsOnboarding(false);
      return data as Profile;
    },
    [userId, supabase]
  );

  const updateProfile = useCallback(
    async (updates: Partial<Profile>) => {
      if (!userId) throw new Error("No user ID");

      const { data, error } = await supabase
        .from("profiles")
        .update(updates)
        .eq("id", userId)
        .select()
        .single();

      if (error) throw error;
      setProfile(data as Profile);
      return data as Profile;
    },
    [userId, supabase]
  );

  return { profile, loading, needsOnboarding, createProfile, updateProfile };
}
