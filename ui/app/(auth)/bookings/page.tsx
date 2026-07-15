"use client";

/**
 * Bookings Page — User's personal booking dashboard.
 *
 * Lists all booking requests with status filtering (pending/approved/rejected)
 * and realtime updates via Supabase WebSockets.
 */

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/lib/hooks/useAuth";
import { useBookings } from "@/lib/hooks/useBookings";
import { Calendar } from "lucide-react";
import BookingCard from "@/components/bookings/booking-card";
import styles from "./page.module.scss";

type StatusFilter = "all" | "pending" | "approved" | "rejected";

export default function BookingsPage() {
  const { user } = useAuth();
  const { bookings, loading, loadBookings } = useBookings(user?.id);
  const [filter, setFilter] = useState<StatusFilter>("all");

  useEffect(() => {
    loadBookings({
      status: filter === "all" ? undefined : filter,
    });
  }, [filter, loadBookings]);

  const filteredBookings =
    filter === "all"
      ? bookings
      : bookings.filter((b) => b.status === filter);

  const FILTERS: { label: string; value: StatusFilter }[] = [
    { label: "All", value: "all" },
    { label: "Pending", value: "pending" },
    { label: "Approved", value: "approved" },
    { label: "Rejected", value: "rejected" },
  ];

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>My Bookings</h1>
        <div className={styles.filterBar}>
          {FILTERS.map((f) => (
            <button
              key={f.value}
              className={`${styles.filterBtn} ${
                filter === f.value ? styles.filterBtnActive : ""
              }`}
              onClick={() => setFilter(f.value)}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className={styles.empty}>
          <span className={styles.emptyText}>Loading bookings...</span>
        </div>
      ) : filteredBookings.length === 0 ? (
        <div className={styles.empty}>
          <div className={styles.emptyIcon}><Calendar size={32} /></div>
          <span className={styles.emptyText}>
            No {filter === "all" ? "" : filter} bookings yet. Start a chat to
            request a room reservation.
          </span>
        </div>
      ) : (
        <div className={styles.grid}>
          {filteredBookings.map((booking) => (
            <BookingCard key={booking.id} booking={booking} />
          ))}
        </div>
      )}
    </div>
  );
}
