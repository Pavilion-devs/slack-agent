-- Update Supabase conversation_sessions table to support bidirectional flow
-- Run this SQL in your Supabase SQL Editor

ALTER TABLE conversation_sessions 
ADD COLUMN IF NOT EXISTS ai_disabled BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS human_assigned_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS assigned_agent_name TEXT;

-- Update existing assigned sessions to have ai_disabled = true
UPDATE conversation_sessions 
SET ai_disabled = TRUE 
WHERE state = 'assigned' AND assigned_to IS NOT NULL;

-- Verify the schema update
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'conversation_sessions' 
AND column_name IN ('ai_disabled', 'human_assigned_at', 'assigned_agent_name');