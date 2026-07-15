-- ============================================================================
-- CSIS SmartAssist — Initial Database Schema
-- ============================================================================

-- Enable pgvector extension for embedding storage
CREATE EXTENSION IF NOT EXISTS vector;

-- ────────────────────────────────────────────────────────────────────────────
-- 1. PROFILES (extends auth.users)
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE public.profiles (
    id              UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email           TEXT NOT NULL,
    full_name       TEXT,
    academic_role   TEXT CHECK (academic_role IN ('undergraduate', 'higher_degree', 'faculty')),
    department      TEXT,
    year            INTEGER,
    interests       TEXT[] DEFAULT '{}',
    synthesized_memory TEXT DEFAULT '',
    is_admin        BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ────────────────────────────────────────────────────────────────────────────
-- 2. DOMAIN RESTRICTION TRIGGER
--    Rejects any sign-up attempt from a non-campus email domain.
-- ────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.enforce_domain_restriction()
RETURNS TRIGGER AS $$
DECLARE
    user_email TEXT;
BEGIN
    user_email := COALESCE(
        NEW.raw_user_meta_data->>'email',
        NEW.email
    );

    IF user_email IS NOT NULL
       AND NOT user_email LIKE '%@goa.bits-pilani.ac.in' THEN
        RAISE EXCEPTION 'Registration restricted: only @goa.bits-pilani.ac.in emails are permitted.';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created_domain_check
    BEFORE INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.enforce_domain_restriction();

-- ────────────────────────────────────────────────────────────────────────────
-- 3. CHAT SESSIONS
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE public.chat_sessions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    title       TEXT NOT NULL DEFAULT 'New Chat',
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ────────────────────────────────────────────────────────────────────────────
-- 4. MESSAGES
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE public.messages (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id          UUID NOT NULL REFERENCES public.chat_sessions(id) ON DELETE CASCADE,
    role                TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content             TEXT NOT NULL,
    interactive_type    TEXT,
    interactive_payload JSONB,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ────────────────────────────────────────────────────────────────────────────
-- 5. RAG FILES (Google Drive source metadata)
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE public.rag_files (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    gdrive_id       TEXT UNIQUE NOT NULL,
    name            TEXT NOT NULL,
    mime_type       TEXT NOT NULL,
    md5_checksum    TEXT NOT NULL,
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ────────────────────────────────────────────────────────────────────────────
-- 6. RAG CHUNKS (Embedded document segments)
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE public.rag_chunks (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_id     UUID NOT NULL REFERENCES public.rag_files(id) ON DELETE CASCADE,
    content     TEXT NOT NULL,
    embedding   vector(768)
);

-- ────────────────────────────────────────────────────────────────────────────
-- 7. BOOKINGS (Space Reservations)
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE public.bookings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    room_id         TEXT NOT NULL,
    room_name       TEXT NOT NULL,
    title           TEXT NOT NULL,
    description     TEXT,
    start_time      TIMESTAMPTZ NOT NULL,
    end_time        TIMESTAMPTZ NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    admin_notes     TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ────────────────────────────────────────────────────────────────────────────
-- 8. INDEXES
-- ────────────────────────────────────────────────────────────────────────────
CREATE INDEX idx_messages_session_id     ON public.messages(session_id);
CREATE INDEX idx_messages_created_at     ON public.messages(created_at);
CREATE INDEX idx_chat_sessions_user_id   ON public.chat_sessions(user_id);
CREATE INDEX idx_chat_sessions_updated   ON public.chat_sessions(updated_at DESC);
CREATE INDEX idx_bookings_user_id        ON public.bookings(user_id);
CREATE INDEX idx_bookings_status         ON public.bookings(status);
CREATE INDEX idx_bookings_start_time     ON public.bookings(start_time);
CREATE INDEX idx_rag_chunks_file_id      ON public.rag_chunks(file_id);

-- HNSW index for fast vector similarity search
CREATE INDEX idx_rag_chunks_embedding ON public.rag_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- ────────────────────────────────────────────────────────────────────────────
-- 9. VECTOR SIMILARITY SEARCH FUNCTION
-- ────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION match_chunks(
    query_embedding vector(768),
    match_threshold FLOAT DEFAULT 0.5,
    match_count     INT DEFAULT 5
)
RETURNS TABLE (
    id         UUID,
    file_id    UUID,
    file_name  TEXT,
    content    TEXT,
    similarity FLOAT
)
LANGUAGE sql STABLE
AS $$
    SELECT
        rc.id,
        rc.file_id,
        rf.name AS file_name,
        rc.content,
        1 - (rc.embedding <=> query_embedding) AS similarity
    FROM public.rag_chunks rc
    JOIN public.rag_files rf ON rf.id = rc.file_id
    WHERE 1 - (rc.embedding <=> query_embedding) > match_threshold
    ORDER BY rc.embedding <=> query_embedding
    LIMIT match_count;
$$;

-- ────────────────────────────────────────────────────────────────────────────
-- 10. ROW-LEVEL SECURITY POLICIES
-- ────────────────────────────────────────────────────────────────────────────

ALTER TABLE public.profiles      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bookings      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.rag_files     ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.rag_chunks    ENABLE ROW LEVEL SECURITY;

-- Profiles
CREATE POLICY "Users can view own profile"
    ON public.profiles FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update own profile"
    ON public.profiles FOR UPDATE USING (auth.uid() = id);
CREATE POLICY "Users can insert own profile"
    ON public.profiles FOR INSERT WITH CHECK (auth.uid() = id);
CREATE POLICY "Admins can view all profiles"
    ON public.profiles FOR SELECT USING (
        EXISTS (SELECT 1 FROM public.profiles p WHERE p.id = auth.uid() AND p.is_admin = TRUE)
    );

-- Chat Sessions
CREATE POLICY "Users manage own sessions"
    ON public.chat_sessions FOR ALL USING (auth.uid() = user_id);

-- Messages (through session ownership)
CREATE POLICY "Users manage own messages"
    ON public.messages FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.chat_sessions cs
            WHERE cs.id = messages.session_id AND cs.user_id = auth.uid()
        )
    );

-- Bookings
CREATE POLICY "Users can view own bookings"
    ON public.bookings FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own bookings"
    ON public.bookings FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Admins can manage all bookings"
    ON public.bookings FOR ALL USING (
        EXISTS (SELECT 1 FROM public.profiles p WHERE p.id = auth.uid() AND p.is_admin = TRUE)
    );

-- RAG tables (read: authenticated, write: admin)
CREATE POLICY "Authenticated users can read rag_files"
    ON public.rag_files FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "Admins can manage rag_files"
    ON public.rag_files FOR ALL USING (
        EXISTS (SELECT 1 FROM public.profiles p WHERE p.id = auth.uid() AND p.is_admin = TRUE)
    );
CREATE POLICY "Authenticated users can read rag_chunks"
    ON public.rag_chunks FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "Admins can manage rag_chunks"
    ON public.rag_chunks FOR ALL USING (
        EXISTS (SELECT 1 FROM public.profiles p WHERE p.id = auth.uid() AND p.is_admin = TRUE)
    );

-- ────────────────────────────────────────────────────────────────────────────
-- 11. REALTIME PUBLICATION
-- ────────────────────────────────────────────────────────────────────────────
ALTER PUBLICATION supabase_realtime ADD TABLE public.bookings;
ALTER PUBLICATION supabase_realtime ADD TABLE public.messages;

-- ────────────────────────────────────────────────────────────────────────────
-- 12. UPDATED_AT TRIGGER (auto-update timestamps)
-- ────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_profiles_updated_at
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

CREATE TRIGGER set_chat_sessions_updated_at
    BEFORE UPDATE ON public.chat_sessions
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

CREATE TRIGGER set_bookings_updated_at
    BEFORE UPDATE ON public.bookings
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();
