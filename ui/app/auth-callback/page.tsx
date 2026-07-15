"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/hooks/useAuth";
import { useGlobalLoading } from "@/lib/contexts/loading-context";
import styles from "./page.module.scss";

export default function AuthCallback() {
  const router = useRouter();
  const { signInWithIdToken } = useAuth();
  const { setGlobalLoading } = useGlobalLoading();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setGlobalLoading(true, "Authenticating securely...");
    
    // Google OIDC Implicit Flow returns the id_token in the URL hash
    const hash = window.location.hash;
    
    if (!hash) {
      setError("No authentication data found.");
      return;
    }

    const params = new URLSearchParams(hash.substring(1));
    const idToken = params.get("id_token");

    if (idToken) {
      const storedNonce = typeof window !== "undefined" ? localStorage.getItem("supabase-auth-nonce") || undefined : undefined;
      signInWithIdToken(idToken, storedNonce)
        .then(() => {
          if (typeof window !== "undefined") {
            localStorage.removeItem("supabase-auth-nonce");
          }
          // Update message for seamless transition
          setGlobalLoading(true, "Loading workspace...");
          // Delay redirect to ensure Supabase SSR sets the cookie
          setTimeout(() => {
            router.replace("/chat");
          }, 500);
        })
        .catch((err) => {
          console.error(err);
          setGlobalLoading(false);
          setError(`Auth failed: ${err.message || JSON.stringify(err)}`);
        });
    } else {
      const errorMsg = params.get("error");
      setGlobalLoading(false);
      if (errorMsg) {
        console.error("Google Auth Error:", errorMsg);
        setError(`Google Auth Error: ${errorMsg}`);
      } else {
        setError("Invalid authentication response.");
      }
    }
  }, [signInWithIdToken]);

  if (error) {
    return (
      <div className={styles.container}>
        <div className={styles.error}>{error}</div>
      </div>
    );
  }

  return null;
}
