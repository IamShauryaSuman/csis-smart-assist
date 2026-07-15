-- Add is_pinned column to chat_sessions table
ALTER TABLE public.chat_sessions 
ADD COLUMN is_pinned BOOLEAN NOT NULL DEFAULT FALSE;

-- Add an index for faster sorting when grouping by pinned status
CREATE INDEX idx_chat_sessions_pinned ON public.chat_sessions(is_pinned, updated_at DESC);
