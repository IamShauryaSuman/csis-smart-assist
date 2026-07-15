"use client";

import { useCallback, useState, useEffect } from "react";
import type { Booking, BookingProposalPayload } from "@/lib/types";
import { FileEdit, Clock, CheckCircle, XCircle } from "lucide-react";
import styles from "./booking-proposal.module.scss";

interface BookingProposalProps {
  payload: BookingProposalPayload;
  bookings: Booking[];
  isLatestDraft?: boolean;
  onCreateBooking: (payload: BookingProposalPayload) => Promise<Booking>;
  onLockBooking: (bookingId: string) => Promise<Booking>;
  onUnlockBooking: (bookingId: string) => Promise<Booking>;
  onUpdateBooking: (bookingId: string, data: any) => Promise<Booking>;
}

type CardState = "draft" | "pending" | "approved" | "rejected" | "expired";

export default function BookingProposal({
  payload,
  bookings,
  isLatestDraft = true,
  onCreateBooking,
  onLockBooking,
  onUnlockBooking,
  onUpdateBooking,
}: BookingProposalProps) {
  const [localError, setLocalError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  
  // Track the most recent matching booking from the DB
  const matchingBookings = bookings
    .filter(
      (b) =>
        b.room_id === payload.room_id &&
        new Date(b.start_time).getTime() === new Date(payload.start_time).getTime() &&
        new Date(b.end_time).getTime() === new Date(payload.end_time).getTime()
    )
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

  const dbBooking = matchingBookings[0] || null;
  const dbStatus = dbBooking?.status;

  const currentState: CardState = dbStatus === "approved" ? "approved" :
                                  dbStatus === "rejected" ? "rejected" :
                                  dbStatus === "expired" ? "expired" :
                                  dbStatus === "pending" ? "pending" : 
                                  !isLatestDraft ? "expired" : "draft";

  // Edit State
  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState({
    title: payload.title,
    room_id: payload.room_id,
    room_name: payload.room_name,
    start_time: payload.start_time.substring(0, 16), // datetime-local format
    end_time: payload.end_time.substring(0, 16),
    description: payload.description || "",
  });

  // Sync form with DB booking if it updates while not editing
  useEffect(() => {
    if (dbBooking && !isEditing) {
      setEditForm({
        title: dbBooking.title,
        room_id: dbBooking.room_id,
        room_name: dbBooking.room_name,
        start_time: dbBooking.start_time.substring(0, 16),
        end_time: dbBooking.end_time.substring(0, 16),
        description: dbBooking.description || "",
      });
    }
  }, [dbBooking, isEditing]);

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

  const handleSubmit = async () => {
    setIsLoading(true);
    setLocalError("");
    try {
      await onCreateBooking({
        room_id: editForm.room_id,
        room_name: editForm.room_name,
        title: editForm.title,
        description: editForm.description,
        start_time: new Date(editForm.start_time).toISOString(),
        end_time: new Date(editForm.end_time).toISOString(),
      });
      // The websocket will update the bookings list and transition state to 'pending'
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : "Failed to create booking.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleEditClick = async () => {
    setLocalError("");
    if (currentState === "pending" && dbBooking) {
      setIsLoading(true);
      try {
        await onLockBooking(dbBooking.id);
        setIsEditing(true);
      } catch (err) {
        setLocalError(err instanceof Error ? err.message : "Failed to lock booking for editing.");
      } finally {
        setIsLoading(false);
      }
    } else if (currentState === "draft") {
      setIsEditing(true);
    }
  };

  const handleCancelEdit = async () => {
    setLocalError("");
    if (currentState === "pending" && dbBooking) {
      setIsLoading(true);
      try {
        await onUnlockBooking(dbBooking.id);
        setIsEditing(false);
      } catch (err) {
        setLocalError("Failed to unlock booking. Please refresh the page.");
      } finally {
        setIsLoading(false);
      }
    } else {
      setIsEditing(false);
    }
  };

  const handleSaveEdit = async () => {
    setLocalError("");
    if (currentState === "pending" && dbBooking) {
      setIsLoading(true);
      try {
        await onUpdateBooking(dbBooking.id, {
          room_id: editForm.room_id,
          room_name: editForm.room_name,
          title: editForm.title,
          description: editForm.description,
          start_time: new Date(editForm.start_time).toISOString(),
          end_time: new Date(editForm.end_time).toISOString(),
        });
        setIsEditing(false);
      } catch (err) {
        setLocalError(err instanceof Error ? err.message : "Failed to update booking.");
      } finally {
        setIsLoading(false);
      }
    } else if (currentState === "draft") {
      setIsEditing(false);
    }
  };

  return (
    <div className={styles.proposal}>
      <div className={styles.header}>
        <span className={`${styles.statusBadge} ${styles[currentState]}`}>
          {currentState === "draft" && <><FileEdit size={16} /> DRAFT PROPOSAL</>}
          {currentState === "pending" && <><Clock size={16} /> PENDING APPROVAL</>}
          {currentState === "approved" && <><CheckCircle size={16} /> APPROVED</>}
          {currentState === "rejected" && <><XCircle size={16} /> REJECTED</>}
          {currentState === "expired" && <><XCircle size={16} /> EXPIRED</>}
        </span>
      </div>

      <div className={styles.details}>
        {isEditing ? (
          <div className={styles.editForm}>
            <div className={styles.infoBanner}>
              To modify the room or timings, please ask the assistant in the chat to check availability.
            </div>
            <div className={styles.row}>
              <span className={styles.rowLabel}>Room</span>
              <span className={styles.rowValue}>{dbBooking?.room_name || editForm.room_name}</span>
            </div>
            <div className={styles.row}>
              <span className={styles.rowLabel}>Start</span>
              <span className={styles.rowValue}>
                {formatDateTime(dbBooking?.start_time || new Date(editForm.start_time).toISOString())}
              </span>
            </div>
            <div className={styles.row}>
              <span className={styles.rowLabel}>End</span>
              <span className={styles.rowValue}>
                {formatDateTime(dbBooking?.end_time || new Date(editForm.end_time).toISOString())}
              </span>
            </div>
            <hr className={styles.divider} />
            <div className={styles.row}>
              <span className={styles.rowLabel}>Title</span>
              <input
                className={styles.input}
                value={editForm.title}
                onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
              />
            </div>
            <div className={styles.row}>
              <span className={styles.rowLabel}>Desc</span>
              <input
                className={styles.input}
                value={editForm.description}
                onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
              />
            </div>
          </div>
        ) : (
          <>
            <div className={styles.row}>
              <span className={styles.rowLabel}>Room</span>
              <span className={styles.rowValue}>{dbBooking?.room_name || editForm.room_name}</span>
            </div>
            <div className={styles.row}>
              <span className={styles.rowLabel}>Title</span>
              <span className={styles.rowValue}>{dbBooking?.title || editForm.title}</span>
            </div>
            <hr className={styles.divider} />
            <div className={styles.row}>
              <span className={styles.rowLabel}>Start</span>
              <span className={styles.rowValue}>
                {formatDateTime(dbBooking?.start_time || new Date(editForm.start_time).toISOString())}
              </span>
            </div>
            <div className={styles.row}>
              <span className={styles.rowLabel}>End</span>
              <span className={styles.rowValue}>
                {formatDateTime(dbBooking?.end_time || new Date(editForm.end_time).toISOString())}
              </span>
            </div>
            {(dbBooking?.description || editForm.description) && (
              <>
                <hr className={styles.divider} />
                <div className={styles.row}>
                  <span className={styles.rowLabel}>Desc</span>
                  <span className={styles.rowValue}>{dbBooking?.description || editForm.description}</span>
                </div>
              </>
            )}
          </>
        )}
      </div>

      {localError && <div className={styles.error}>{localError}</div>}

      <div className={styles.actions}>
        {isEditing ? (
          <>
            <button className={styles.dismissBtn} onClick={handleCancelEdit} disabled={isLoading}>
              Cancel
            </button>
            <button className={styles.confirmBtn} onClick={handleSaveEdit} disabled={isLoading}>
              {isLoading ? "Saving..." : "Save"}
            </button>
          </>
        ) : (
          <>
            {(currentState === "draft" || currentState === "pending") && (
              <button className={styles.dismissBtn} onClick={handleEditClick} disabled={isLoading}>
                {isLoading ? "Loading..." : "Edit"}
              </button>
            )}
            
            {currentState === "draft" && (
              <button className={styles.confirmBtn} onClick={handleSubmit} disabled={isLoading}>
                {isLoading ? "Submitting..." : "Submit Request"}
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
}
