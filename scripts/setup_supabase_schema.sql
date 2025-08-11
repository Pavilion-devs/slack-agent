-- Supabase Database Schema for Slack Responder Agent System
-- Run this script in your Supabase SQL editor to create the required tables

-- Create conversation_sessions table
CREATE TABLE IF NOT EXISTS conversation_sessions (
    id SERIAL PRIMARY KEY,
    session_id UUID UNIQUE NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    channel_id VARCHAR(255) NOT NULL,
    thread_ts VARCHAR(255),
    state VARCHAR(20) NOT NULL CHECK (state IN ('active', 'assigned', 'closed')),
    assigned_to VARCHAR(255),
    escalated_at TIMESTAMPTZ NOT NULL,
    escalation_reason TEXT NOT NULL,
    history JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_sessions_session_id ON conversation_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON conversation_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_state ON conversation_sessions(state);
CREATE INDEX IF NOT EXISTS idx_sessions_assigned_to ON conversation_sessions(assigned_to);
CREATE INDEX IF NOT EXISTS idx_sessions_escalated_at ON conversation_sessions(escalated_at);
CREATE INDEX IF NOT EXISTS idx_sessions_thread_ts ON conversation_sessions(thread_ts);

-- Create composite index for common queries
CREATE INDEX IF NOT EXISTS idx_sessions_user_state ON conversation_sessions(user_id, state);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to automatically update updated_at column
DROP TRIGGER IF EXISTS update_conversation_sessions_updated_at ON conversation_sessions;
CREATE TRIGGER update_conversation_sessions_updated_at
    BEFORE UPDATE ON conversation_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create agent_metrics table for tracking performance
CREATE TABLE IF NOT EXISTS agent_metrics (
    id SERIAL PRIMARY KEY,
    agent_slack_id VARCHAR(255) NOT NULL,
    agent_name VARCHAR(255),
    sessions_handled INTEGER DEFAULT 0,
    avg_response_time_minutes DECIMAL(10,2),
    total_messages_sent INTEGER DEFAULT 0,
    sessions_closed INTEGER DEFAULT 0,
    last_activity TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for agent_metrics
CREATE INDEX IF NOT EXISTS idx_agent_metrics_slack_id ON agent_metrics(agent_slack_id);
CREATE INDEX IF NOT EXISTS idx_agent_metrics_last_activity ON agent_metrics(last_activity);

-- Create updated_at trigger for agent_metrics
DROP TRIGGER IF EXISTS update_agent_metrics_updated_at ON agent_metrics;
CREATE TRIGGER update_agent_metrics_updated_at
    BEFORE UPDATE ON agent_metrics
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create escalation_logs table for audit trail
CREATE TABLE IF NOT EXISTS escalation_logs (
    id SERIAL PRIMARY KEY,
    session_id UUID REFERENCES conversation_sessions(session_id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL, -- 'created', 'assigned', 'message_sent', 'closed'
    actor_type VARCHAR(20) NOT NULL, -- 'user', 'agent', 'system'
    actor_id VARCHAR(255),
    details JSONB,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for escalation_logs
CREATE INDEX IF NOT EXISTS idx_escalation_logs_session_id ON escalation_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_escalation_logs_event_type ON escalation_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_escalation_logs_timestamp ON escalation_logs(timestamp);

-- Create system_health table for monitoring
CREATE TABLE IF NOT EXISTS system_health (
    id SERIAL PRIMARY KEY,
    component VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL, -- 'healthy', 'degraded', 'down'
    details JSONB,
    last_check TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create unique constraint on component for system_health
CREATE UNIQUE INDEX IF NOT EXISTS idx_system_health_component ON system_health(component);

-- Insert initial system health records
INSERT INTO system_health (component, status, details) 
VALUES 
    ('responder_agent', 'healthy', '{"initialized": true}'),
    ('session_manager', 'healthy', '{"supabase_connected": true}'),
    ('slack_thread_manager', 'healthy', '{"slack_api_connected": true}')
ON CONFLICT (component) DO NOTHING;

-- Create Row Level Security (RLS) policies
ALTER TABLE conversation_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE escalation_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_health ENABLE ROW LEVEL SECURITY;

-- Create policy for service role (full access)
CREATE POLICY "Service role can manage all data" ON conversation_sessions
FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role can manage agent metrics" ON agent_metrics
FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role can manage escalation logs" ON escalation_logs
FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role can manage system health" ON system_health
FOR ALL USING (auth.role() = 'service_role');

-- Create views for common queries
CREATE OR REPLACE VIEW active_escalations AS
SELECT 
    s.*,
    EXTRACT(EPOCH FROM (NOW() - s.escalated_at)) / 60 as minutes_since_escalation
FROM conversation_sessions s
WHERE s.state IN ('active', 'assigned')
ORDER BY s.escalated_at ASC;

CREATE OR REPLACE VIEW agent_performance AS
SELECT 
    am.agent_slack_id,
    am.agent_name,
    am.sessions_handled,
    am.sessions_closed,
    CASE 
        WHEN am.sessions_handled > 0 
        THEN (am.sessions_closed::DECIMAL / am.sessions_handled) * 100 
        ELSE 0 
    END as close_rate_percentage,
    am.avg_response_time_minutes,
    am.total_messages_sent,
    am.last_activity
FROM agent_metrics am
WHERE am.sessions_handled > 0
ORDER BY am.sessions_handled DESC;

CREATE OR REPLACE VIEW escalation_summary AS
SELECT 
    COUNT(*) as total_sessions,
    COUNT(*) FILTER (WHERE state = 'active') as active_sessions,
    COUNT(*) FILTER (WHERE state = 'assigned') as assigned_sessions,
    COUNT(*) FILTER (WHERE state = 'closed') as closed_sessions,
    AVG(EXTRACT(EPOCH FROM (updated_at - escalated_at)) / 60) FILTER (WHERE state = 'closed') as avg_resolution_time_minutes,
    COUNT(*) FILTER (WHERE escalated_at > NOW() - INTERVAL '24 hours') as escalations_last_24h,
    COUNT(*) FILTER (WHERE escalated_at > NOW() - INTERVAL '7 days') as escalations_last_7d
FROM conversation_sessions;

-- Create function to cleanup old closed sessions
CREATE OR REPLACE FUNCTION cleanup_old_sessions(days_old INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM conversation_sessions 
    WHERE state = 'closed' 
    AND updated_at < NOW() - (days_old || ' days')::INTERVAL;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    INSERT INTO escalation_logs (session_id, event_type, actor_type, details)
    VALUES (NULL, 'cleanup', 'system', 
            jsonb_build_object('deleted_sessions', deleted_count, 'days_old', days_old));
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Create function to update agent metrics
CREATE OR REPLACE FUNCTION update_agent_metrics(
    p_agent_slack_id VARCHAR(255),
    p_agent_name VARCHAR(255),
    p_session_handled BOOLEAN DEFAULT FALSE,
    p_session_closed BOOLEAN DEFAULT FALSE,
    p_message_sent BOOLEAN DEFAULT FALSE,
    p_response_time_minutes DECIMAL DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
    INSERT INTO agent_metrics (
        agent_slack_id, 
        agent_name, 
        sessions_handled, 
        sessions_closed, 
        total_messages_sent,
        avg_response_time_minutes,
        last_activity
    ) VALUES (
        p_agent_slack_id, 
        p_agent_name, 
        CASE WHEN p_session_handled THEN 1 ELSE 0 END,
        CASE WHEN p_session_closed THEN 1 ELSE 0 END,
        CASE WHEN p_message_sent THEN 1 ELSE 0 END,
        p_response_time_minutes,
        NOW()
    )
    ON CONFLICT (agent_slack_id) 
    DO UPDATE SET
        agent_name = EXCLUDED.agent_name,
        sessions_handled = agent_metrics.sessions_handled + EXCLUDED.sessions_handled,
        sessions_closed = agent_metrics.sessions_closed + EXCLUDED.sessions_closed,
        total_messages_sent = agent_metrics.total_messages_sent + EXCLUDED.total_messages_sent,
        avg_response_time_minutes = CASE 
            WHEN EXCLUDED.avg_response_time_minutes IS NOT NULL 
            THEN (COALESCE(agent_metrics.avg_response_time_minutes, 0) + EXCLUDED.avg_response_time_minutes) / 2
            ELSE agent_metrics.avg_response_time_minutes
        END,
        last_activity = EXCLUDED.last_activity,
        updated_at = NOW();
END;
$$ LANGUAGE plpgsql;

-- Create index on agent_metrics for the upsert operation
CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_metrics_slack_id_unique ON agent_metrics(agent_slack_id);

-- Create function to log escalation events
CREATE OR REPLACE FUNCTION log_escalation_event(
    p_session_id UUID,
    p_event_type VARCHAR(50),
    p_actor_type VARCHAR(20),
    p_actor_id VARCHAR(255) DEFAULT NULL,
    p_details JSONB DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
    INSERT INTO escalation_logs (session_id, event_type, actor_type, actor_id, details)
    VALUES (p_session_id, p_event_type, p_actor_type, p_actor_id, p_details);
END;
$$ LANGUAGE plpgsql;

-- Grant necessary permissions
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO service_role;

-- Insert sample test data (optional - remove in production)
-- INSERT INTO conversation_sessions (session_id, user_id, channel_id, state, escalation_reason, escalated_at)
-- VALUES 
--     ('550e8400-e29b-41d4-a716-446655440000', 'test_user_1', 'chainlit_test', 'active', 'Testing escalation system', NOW()),
--     ('550e8400-e29b-41d4-a716-446655440001', 'test_user_2', 'web_interface', 'assigned', 'Complex pricing question', NOW() - INTERVAL '30 minutes');

COMMIT;