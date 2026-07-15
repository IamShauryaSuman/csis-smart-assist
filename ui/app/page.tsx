"use client";

import { useEffect, useState, Suspense, useRef } from "react";
import { useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/hooks/useAuth";
import dynamic from "next/dynamic";
import styles from "./page.module.scss";

// Lazy-load the 3D canvas to avoid SSR issues with Three.js
const PolyhedronCanvas = dynamic(
  () => import("@/components/layout/polyhedron-canvas"),
  { ssr: false }
);

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"
        fill="#4285F4"
      />
      <path
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
        fill="#34A853"
      />
      <path
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
        fill="#FBBC05"
      />
      <path
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
        fill="#EA4335"
      />
    </svg>
  );
}

function GithubIcon() {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
      <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
    </svg>
  );
}

function LandingContent() {
  const { user, loading, signInWithGoogle } = useAuth();
  const searchParams = useSearchParams();
  const [authError, setAuthError] = useState(false);
  const [systemStatus, setSystemStatus] = useState<"checking" | "online" | "offline">("checking");
  const landingRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (searchParams.get("error") === "auth_failed") {
      setAuthError(true);
      const timer = setTimeout(() => setAuthError(false), 5000);
      return () => clearTimeout(timer);
    }
  }, [searchParams]);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (landingRef.current) {
        landingRef.current.style.setProperty("--mouse-x", `${e.clientX}px`);
        landingRef.current.style.setProperty("--mouse-y", `${e.clientY}px`);
      }
    };
    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, []);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const envUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const baseUrl = envUrl.replace(/\/$/, "");
        const res = await fetch(`${baseUrl}/health`);
        if (res.ok) {
          setSystemStatus("online");
        } else {
          setSystemStatus("offline");
        }
      } catch (err) {
        setSystemStatus("offline");
      }
    };
    fetchHealth();
  }, []);

  // Redirect authenticated users
  useEffect(() => {
    if (user && !loading) {
      window.location.href = "/chat";
    }
  }, [user, loading]);

  return (
    <div className={styles.landing} ref={landingRef}>
      <div className={styles.mouseGlow} />
      {/* 3D Background */}
      <div className={styles.canvasWrapper}>
        <PolyhedronCanvas />
      </div>

      {/* Error Banner */}
      {authError && (
        <div className={styles.errorBanner}>
          Authentication failed. Only @goa.bits-pilani.ac.in emails are
          permitted.
        </div>
      )}

      {/* Header */}
      <header className={styles.header}>
        <div className={styles.logo}>
          <div className={styles.statusBadge}>
            <span className={`${styles.statusDot} ${styles[systemStatus]}`}></span>
            {systemStatus}
          </div>
        </div>
        <nav className={styles.headerLinks}>
          <a
            href="https://github.com/IamShauryaSuman/csis-smartassist"
            target="_blank"
            rel="noopener noreferrer"
            className={styles.githubLink}
          >
            <GithubIcon />
            <span>contribute</span>
          </a>
        </nav>
      </header>

      {/* Hero */}
      <main className={styles.hero}>
        <div className={styles.heroContent}>
          <div className={styles.titleWrapper}>
            <div className={styles.titlePrefix}>CSIS</div>
            <h1 className={styles.titleMain}>SmartAssist</h1>
          </div>
          <div className={styles.subtitleWrapper}>
            BITS PILANI, K K BIRLA GOA CAMPUS
          </div>
          
          <div className={styles.divider}></div>
          
          <p className={styles.description}>
            Instant answers about courses, syllabi, and policies.<br/>
            Automated lab and room reservations. Built for the CSIS community.
          </p>
          <button
            className={styles.authButton}
            onClick={signInWithGoogle}
            disabled={loading}
            id="google-sign-in"
          >
            <div className={styles.googleIconWrapper}>
              <GoogleIcon />
            </div>
            <span>{loading ? "SIGNING IN..." : "SIGN IN WITH GOOGLE"}</span>
          </button>
        </div>
      </main>


      {/* Footer */}
      <footer className={styles.footer}>
        <p>
          Computer Science & Information Systems Department — BITS Pilani, K K
          Birla Goa Campus
        </p>
      </footer>
    </div>
  );
}

export default function LandingPage() {
  return (
    <Suspense>
      <LandingContent />
    </Suspense>
  );
}
