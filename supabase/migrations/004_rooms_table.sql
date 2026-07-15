-- 004_rooms_table.sql
-- Create rooms table and insert seed data

CREATE TABLE IF NOT EXISTS rooms (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    capacity INTEGER NOT NULL,
    hardware TEXT[] NOT NULL DEFAULT '{}',
    calendar_id TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable RLS
ALTER TABLE rooms ENABLE ROW LEVEL SECURITY;

-- Policies
-- Anyone authenticated can read rooms
CREATE POLICY "Authenticated users can read rooms"
    ON rooms FOR SELECT
    TO authenticated
    USING (true);

-- Only admins can insert/update/delete rooms
CREATE POLICY "Admins can manage rooms"
    ON rooms FOR ALL
    TO authenticated
    USING (EXISTS (SELECT 1 FROM public.profiles p WHERE p.id = auth.uid() AND p.is_admin = TRUE))
    WITH CHECK (EXISTS (SELECT 1 FROM public.profiles p WHERE p.id = auth.uid() AND p.is_admin = TRUE));

-- Insert seed data
INSERT INTO rooms (id, name, type, capacity, hardware, calendar_id, description)
VALUES
    (
        'lab_1',
        'Computer Lab 1 (D-311)',
        'computer_lab',
        60,
        ARRAY['Desktop PCs (i7, 16GB RAM)', 'Projector', 'Whiteboard', 'LAN'],
        'csis_lab1@group.calendar.google.com',
        'Primary teaching lab with 60 workstations. Suitable for programming courses and examinations.'
    ),
    (
        'lab_2',
        'Computer Lab 2 (D-312)',
        'computer_lab',
        40,
        ARRAY['Desktop PCs (i5, 8GB RAM)', 'Projector', 'Whiteboard'],
        'csis_lab2@group.calendar.google.com',
        'Secondary teaching lab. Good for smaller lab sessions and tutorials.'
    ),
    (
        'seminar_1',
        'Main Seminar Hall (Ground Floor)',
        'seminar_hall',
        120,
        ARRAY['Dual Projectors', 'PA System', 'Podium with Mic', 'Air Conditioning'],
        'csis_seminar1@group.calendar.google.com',
        'Large hall for guest lectures, department orientations, and major presentations.'
    ),
    (
        'meeting_1',
        'Faculty Meeting Room (D-302)',
        'meeting_room',
        12,
        ARRAY['Smart TV (55")', 'Video Conferencing', 'Whiteboard', 'Wi-Fi'],
        'csis_meeting1@group.calendar.google.com',
        'Compact meeting space for faculty meetings, student consultations, and interviews.'
    ),
    (
        'dlt_8',
        'DLT-8',
        'lecture_hall',
        150,
        ARRAY['Projector', 'Whiteboard', 'Microphone', 'Air Conditioning'],
        'csis_dlt8@group.calendar.google.com',
        'Department Lecture Theatre 8.'
    )
ON CONFLICT (id) DO NOTHING;
