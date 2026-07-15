"use client";

/**
 * Auth Layout — Wraps all authenticated routes.
 *
 * Handles auth state checking, profile loading, onboarding interception,
 * and provides the persistent Navbar. Redirects unauthenticated users
 * to the landing page.
 */

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/lib/hooks/useAuth";
import { useProfile } from "@/lib/hooks/useProfile";
import Navbar from "@/components/layout/navbar";
import { useGlobalLoading } from "@/lib/contexts/loading-context";
import styles from "./layout.module.scss";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, loading: authLoading } = useAuth();
  const { profile, loading: profileLoading, needsOnboarding } = useProfile(
    user?.id
  );
  const { setGlobalLoading } = useGlobalLoading();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (authLoading || profileLoading) return;

    if (!user) {
      router.replace("/");
      return;
    }

    // Intercept: redirect to onboarding if profile incomplete
    if (needsOnboarding && pathname !== "/onboarding") {
      router.replace("/onboarding");
      return;
    }

    // Redirect away from onboarding if profile is complete
    if (!needsOnboarding && pathname === "/onboarding") {
      router.replace("/chat");
      return;
    }

    setReady(true);
  }, [
    user,
    authLoading,
    profileLoading,
    needsOnboarding,
    pathname,
    router,
  ]);

  // Sync with global loading state
  useEffect(() => {
    if (authLoading || profileLoading || !ready) {
      setGlobalLoading(true, "Loading workspace...");
    } else {
      setGlobalLoading(false);
    }
    
    // Safety cleanup in case layout unmounts
    return () => setGlobalLoading(false);
  }, [authLoading, profileLoading, ready, setGlobalLoading]);

  // Loading state
  if (authLoading || profileLoading || !ready) {
    return null;
  }

  // Onboarding page gets no navbar
  if (pathname === "/onboarding") {
    return <>{children}</>;
  }

  return (
    <div className={styles.layoutWrapper}>
      <Navbar profile={profile} />
      <main className={styles.mainContent}>
        {children}
      </main>
    </div>
  );
}
