/**
 * OAuth callback route — handles the redirect from Google OAuth.
 *
 * Exchanges the authorization code for a session and redirects
 * the user to the chat page (or onboarding if needed).
 */

import { NextResponse } from "next/server";
import { createServerSupabaseClient } from "@/lib/supabase/server";

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  const next = searchParams.get("next") ?? "/chat";

  if (code) {
    const supabase = await createServerSupabaseClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);

    if (!error) {
      // Check if user has a profile (onboarding check)
      const {
        data: { user },
      } = await supabase.auth.getUser();

      if (user) {
        const { data: profile } = await supabase
          .from("profiles")
          .select("academic_role")
          .eq("id", user.id)
          .single();

        if (!profile || !profile.academic_role) {
          return NextResponse.redirect(`${origin}/onboarding`);
        }
      }

      return NextResponse.redirect(`${origin}${next}`);
    }
  }

  // Auth error — redirect to landing with error indicator
  return NextResponse.redirect(`${origin}/?error=auth_failed`);
}
