/**
 * Supabase browser client — for use in Client Components.
 *
 * Uses the public anon key; all operations respect RLS policies.
 * Auth state is persisted via cookies managed by @supabase/ssr.
 */

import { createBrowserClient } from "@supabase/ssr";

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL || "https://placeholder.supabase.co",
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "placeholder"
  );
}
