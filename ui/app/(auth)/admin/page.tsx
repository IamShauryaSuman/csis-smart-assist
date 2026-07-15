"use client";

/**
 * Admin Page — Department management dashboard.
 *
 * Two-tab interface:
 * 1. Booking Approval Matrix — review and approve/reject booking requests
 * 2. RAG Pipeline Dashboard — sync knowledge base from Google Drive
 *
 * Access restricted to users with is_admin=true.
 */

import { useState } from "react";
import { useAuth } from "@/lib/hooks/useAuth";
import { useProfile } from "@/lib/hooks/useProfile";
import { Lock } from "lucide-react";
import AdminBookingTable from "@/components/bookings/admin-booking-table";
import RagDashboard from "@/components/dashboard/rag-dashboard";
import styles from "./page.module.scss";

type AdminTab = "bookings" | "rag";

export default function AdminPage() {
  const { user } = useAuth();
  const { profile } = useProfile(user?.id);
  const [activeTab, setActiveTab] = useState<AdminTab>("bookings");

  // Access control
  if (!profile?.is_admin) {
    return (
      <div className={styles.page}>
        <div className={styles.accessDenied}>
          <div className={styles.accessIcon}><Lock size={32} /></div>
          <span className={styles.accessText}>
            Access restricted to department administrators.
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>Admin Dashboard</h1>
        <p className={styles.subtitle}>
          Manage booking approvals and the RAG knowledge base pipeline.
        </p>
      </div>

      <div className={styles.tabs}>
        <button
          className={`${styles.tab} ${
            activeTab === "bookings" ? styles.tabActive : ""
          }`}
          onClick={() => setActiveTab("bookings")}
          id="tab-bookings"
        >
          Booking Approvals
        </button>
        <button
          className={`${styles.tab} ${
            activeTab === "rag" ? styles.tabActive : ""
          }`}
          onClick={() => setActiveTab("rag")}
          id="tab-rag"
        >
          RAG Pipeline
        </button>
      </div>

      <div className={styles.section}>
        {activeTab === "bookings" ? (
          <AdminBookingTable userId={user!.id} />
        ) : (
          <RagDashboard />
        )}
      </div>
    </div>
  );
}
