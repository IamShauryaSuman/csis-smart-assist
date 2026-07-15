"use client";

/**
 * AdminBookingTable — Booking approval matrix for administrators.
 *
 * Displays all pending/approved/rejected bookings with inline
 * approval actions, admin notes, and status filtering.
 */

import { useCallback, useEffect, useState } from "react";
import { useBookings } from "@/lib/hooks/useBookings";
import type { Booking } from "@/lib/types";
import { Lock } from "lucide-react";
import styles from "./admin-booking-table.module.scss";

interface AdminBookingTableProps {
  userId: string;
}

type StatusFilter = "all" | "pending" | "approved" | "rejected";

export default function AdminBookingTable({ userId }: AdminBookingTableProps) {
  const { bookings, loading, loadBookings, updateBookingStatus } =
    useBookings(userId);
  const [filter, setFilter] = useState<StatusFilter>("pending");
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [processing, setProcessing] = useState<string | null>(null);

  useEffect(() => {
    loadBookings({
      allUsers: true,
      status: filter === "all" ? undefined : filter,
    });
  }, [filter, loadBookings]);

  const handleAction = useCallback(
    async (bookingId: string, status: "approved" | "rejected") => {
      setProcessing(bookingId);
      try {
        await updateBookingStatus(bookingId, status, notes[bookingId] || "");
        setNotes((prev) => {
          const next = { ...prev };
          delete next[bookingId];
          return next;
        });
      } catch (error) {
        console.error("Failed to update booking:", error);
      } finally {
        setProcessing(null);
      }
    },
    [updateBookingStatus, notes]
  );

  const formatDateTime = (iso: string) => {
    try {
      return new Date(iso).toLocaleString("en-IN", {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return iso;
    }
  };

  const statusClass = (status: string) =>
    ({
      pending: styles.statusPending,
      approved: styles.statusApproved,
      rejected: styles.statusRejected,
    })[status] || "";

  const FILTERS: { label: string; value: StatusFilter }[] = [
    { label: "Pending", value: "pending" },
    { label: "Approved", value: "approved" },
    { label: "Rejected", value: "rejected" },
    { label: "All", value: "all" },
  ];

  return (
    <div>
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

      {loading ? (
        <div className={styles.empty}>Loading bookings...</div>
      ) : bookings.length === 0 ? (
        <div className={styles.empty}>
          No {filter === "all" ? "" : filter} bookings found.
        </div>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Title</th>
                <th>Room</th>
                <th>Time</th>
                <th>Status</th>
                <th>Notes</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {bookings.map((booking: Booking) => (
                <tr key={booking.id}>
                  <td className={styles.titleCell}>
                    <div className={styles.bookingTitle}>{booking.title}</div>
                    {booking.description && (
                      <div className={styles.bookingDescription}>{booking.description}</div>
                    )}
                  </td>
                  <td>{booking.room_name}</td>
                  <td>
                    {formatDateTime(booking.start_time)}
                    <br />→ {formatDateTime(booking.end_time)}
                  </td>
                  <td>
                    <span className={statusClass(booking.status)}>
                      {booking.status.toUpperCase()}
                    </span>
                  </td>
                  <td>
                    {booking.status === "pending" ? (
                      <input
                        className={styles.notesInput}
                        placeholder="Admin notes..."
                        value={notes[booking.id] || ""}
                        onChange={(e) =>
                          setNotes((prev) => ({
                            ...prev,
                            [booking.id]: e.target.value,
                          }))
                        }
                      />
                    ) : (
                      booking.admin_notes || "—"
                    )}
                  </td>
                  <td>
                    {booking.status === "pending" ? (
                      <div className={styles.actions}>
                        {booking.is_locked ? (
                          <span className={styles.lockedIndicator} title="User is currently editing this booking">
                            <Lock size={14} /> Locked for edit
                          </span>
                        ) : (
                          <>
                            <button
                              className={styles.approveBtn}
                              onClick={() => handleAction(booking.id, "approved")}
                              disabled={processing === booking.id}
                            >
                              {processing === booking.id ? "..." : "Approve"}
                            </button>
                            <button
                              className={styles.rejectBtn}
                              onClick={() => handleAction(booking.id, "rejected")}
                              disabled={processing === booking.id}
                            >
                              Reject
                            </button>
                          </>
                        )}
                      </div>
                    ) : (
                      "—"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
