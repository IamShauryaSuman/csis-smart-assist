-- 005_booking_locks.sql
-- Add locking mechanism columns to the bookings table

ALTER TABLE bookings ADD COLUMN IF NOT EXISTS is_locked BOOLEAN DEFAULT FALSE;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS locked_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS locked_by UUID REFERENCES auth.users(id);

-- Only the user who created the booking (or admin) can lock it. We don't need strict RLS for this since the API routes will enforce it, but we already have RLS on bookings.
