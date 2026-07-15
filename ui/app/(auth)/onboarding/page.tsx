"use client";

/**
 * Onboarding Page — Non-dismissible profile setup for new users.
 *
 * Captures academic role, department, year, and interests
 * before allowing access to the main application.
 */

import { useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/hooks/useAuth";
import { useProfile } from "@/lib/hooks/useProfile";
import OnboardingForm from "@/components/auth/onboarding-form";
import type { OnboardingFormData } from "@/lib/types";
import styles from "./page.module.scss";

export default function OnboardingPage() {
  const router = useRouter();
  const { user } = useAuth();
  const { createProfile } = useProfile(user?.id);

  const handleSubmit = useCallback(
    async (data: OnboardingFormData) => {
      await createProfile(data);
      window.location.href = "/chat";
    },
    [createProfile]
  );

  return (
    <div className={styles.page}>
      <div className={styles.container}>
        <div className={styles.header}>
          <div className={styles.logoMark}>CSIS</div>
          <h1 className={styles.title}>Welcome to SmartAssist</h1>
          <p className={styles.subtitle}>
            Let&apos;s set up your profile to personalize your experience.
          </p>
        </div>
        <OnboardingForm onSubmit={handleSubmit} />
      </div>
    </div>
  );
}
