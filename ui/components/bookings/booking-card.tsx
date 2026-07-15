"use client";

/**
 * BookingCard — Displays a single booking request with status badge.
 *
 * Used in the /bookings dashboard and /admin approval matrix.
 * Supports realtime status updates via Supabase WebSockets.
 */

import type { Booking } from "@/lib/types";
import { MapPin, Clock, FileText } from "lucide-react";
import styles from "./booking-card.module.scss";

interface BookingCardProps {
  booking: Booking;
}

export default function BookingCard({ booking }: BookingCardProps) {
  const formatDateTime = (iso: string) => {
    try {
      return new Date(iso).toLocaleString("en-IN", {
        weekday: "short",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return iso;
    }
  };

  const statusMap: Record<string, string> = {
    pending: styles.statusPending,
    approved: styles.statusApproved,
    rejected: styles.statusRejected,
    expired: styles.statusRejected,
  };
  const statusClass = statusMap[booking.status] || styles.statusPending;

  return (
    <div className={styles.card}>
      <div className={styles.top}>
        <span className={styles.title}>{booking.title}</span>
        <span className={statusClass}>
          {booking.status.toUpperCase()}
        </span>
      </div>

      <div className={styles.details}>
        <div className={styles.row}>
          <span className={styles.icon}><MapPin size={14} /></span>
          <span className={styles.value}>{booking.room_name}</span>
        </div>
        <div className={styles.row}>
          <span className={styles.icon}><Clock size={14} /></span>
          <span className={styles.value}>
            {formatDateTime(booking.start_time)} → {formatDateTime(booking.end_time)}
          </span>
        </div>
        {booking.description && (
          <div className={styles.row}>
            <span className={styles.icon}><FileText size={14} /></span>
            <span className={styles.value}>{booking.description}</span>
          </div>
        )}
      </div>

      {booking.admin_notes && (
        <div className={styles.notes}>
          <div className={styles.notesLabel}>Admin Notes</div>
          <div className={styles.notesText}>{booking.admin_notes}</div>
        </div>
      )}
    </div>
  );
}
