-- 006_booking_expired_status.sql

-- If the status column is using a check constraint, we need to alter the constraint to allow 'expired'
-- Since we didn't use an ENUM type and just used a text column with a check constraint (or no constraint),
-- we don't necessarily have to do DDL unless there's an explicit constraint. 

-- In 001_initial_schema.sql: 
-- status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),

ALTER TABLE bookings DROP CONSTRAINT IF EXISTS bookings_status_check;
ALTER TABLE bookings ADD CONSTRAINT bookings_status_check CHECK (status IN ('pending', 'approved', 'rejected', 'expired'));
