/**
 * useBookings — Booking state management with Supabase Realtime.
 *
 * Manages user bookings, creation from chat proposals,
 * and real-time status updates via Supabase WebSockets.
 */

"use client";

import { useCallback, useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { api } from "@/lib/api";
import type { Booking, BookingProposalPayload } from "@/lib/types";

export function useBookings(userId: string | undefined) {
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [loading, setLoading] = useState(false);
  const supabase = createClient();

  const loadBookings = useCallback(
    async (options: { status?: string; allUsers?: boolean } = {}) => {
      setLoading(true);
      try {
        const data = await api.listBookings(options);
        setBookings(data);
      } catch (error) {
        console.error("Failed to load bookings:", error);
      } finally {
        setLoading(false);
      }
    },
    []
  );

  // Subscribe to realtime booking updates
  useEffect(() => {
    if (!userId) return;

    const channel = supabase
      .channel(`bookings-realtime-${Math.random()}`)
      .on(
        "postgres_changes",
        {
          event: "*",
          schema: "public",
          table: "bookings",
          filter: `user_id=eq.${userId}`,
        },
        (payload) => {
          if (payload.eventType === "INSERT") {
            setBookings((prev) => [payload.new as Booking, ...prev]);
          } else if (payload.eventType === "UPDATE") {
            setBookings((prev) =>
              prev.map((b) =>
                b.id === (payload.new as Booking).id
                  ? (payload.new as Booking)
                  : b
              )
            );
          } else if (payload.eventType === "DELETE") {
            setBookings((prev) =>
              prev.filter((b) => b.id !== (payload.old as { id: string }).id)
            );
          }
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [userId, supabase]);

  const createBooking = useCallback(
    async (proposal: BookingProposalPayload) => {
      try {
        const booking = await api.createBooking({
          room_id: proposal.room_id,
          room_name: proposal.room_name,
          title: proposal.title,
          start_time: proposal.start_time,
          end_time: proposal.end_time,
          description: proposal.description,
        });
        setBookings((prev) => [booking, ...prev]);
        return booking;
      } catch (error) {
        console.error("Failed to create booking:", error);
        throw error;
      }
    },
    []
  );

  const updateBookingStatus = useCallback(
    async (
      bookingId: string,
      status: "approved" | "rejected",
      adminNotes?: string
    ) => {
      try {
        const updated = await api.updateBookingStatus(
          bookingId,
          status,
          adminNotes
        );
        setBookings((prev) =>
          prev.map((b) => (b.id === bookingId ? updated : b))
        );
        return updated;
      } catch (error) {
        console.error("Failed to update booking:", error);
        throw error;
      }
    },
    []
  );

  const lockBooking = useCallback(async (bookingId: string) => {
    try {
      const updated = await api.lockBooking(bookingId);
      setBookings((prev) => prev.map((b) => (b.id === bookingId ? updated : b)));
      return updated;
    } catch (error) {
      console.error("Failed to lock booking:", error);
      throw error;
    }
  }, []);

  const unlockBooking = useCallback(async (bookingId: string) => {
    try {
      const updated = await api.unlockBooking(bookingId);
      setBookings((prev) => prev.map((b) => (b.id === bookingId ? updated : b)));
      return updated;
    } catch (error) {
      console.error("Failed to unlock booking:", error);
      throw error;
    }
  }, []);

  const updateBookingDetails = useCallback(async (
    bookingId: string,
    data: { room_id: string; room_name: string; title: string; description?: string; start_time: string; end_time: string; }
  ) => {
    try {
      const updated = await api.updateBookingDetails(bookingId, data);
      setBookings((prev) => prev.map((b) => (b.id === bookingId ? updated : b)));
      return updated;
    } catch (error) {
      console.error("Failed to update booking details:", error);
      throw error;
    }
  }, []);

  return {
    bookings,
    loading,
    loadBookings,
    createBooking,
    updateBookingStatus,
    lockBooking,
    unlockBooking,
    updateBookingDetails,
  };
}
