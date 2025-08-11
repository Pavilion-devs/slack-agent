# Session Storage System Documentation

## Overview

The Delve AI Agent uses a **sophisticated session management system** built on Supabase PostgreSQL to handle conversation persistence, agent assignment, and bidirectional messaging between users and human support agents.

## Architecture Components

### 1. SessionManager (`src/core/session_manager.py`)
**Primary database interface for conversation sessions**

**Key Features:**
- **UUID-based session tracking**: Each conversation gets a unique session ID
- **Multi-state management**: ACTIVE → ASSIGNED → CLOSED workflow
- **JSON history storage**: Complete conversation context preserved
- **Agent assignment tracking**: Links sessions to specific Slack agents
- **Timezone-aware timestamps**: All times stored in UTC

### 2. ConversationSession Data Model
```python
@dataclass
class ConversationSession:
    session_id: str              # UUID identifier
    user_id: str                 # Platform-specific user ID
    channel_id: str              # Channel where conversation started
    thread_ts: Optional[str]     # Slack thread timestamp
    state: SessionState          # ACTIVE, ASSIGNED, or CLOSED
    assigned_to: Optional[str]   # Slack agent user ID
    escalated_at: datetime       # When escalation occurred
    escalation_reason: str       # Why it was escalated
    history: List[Dict[str, Any]]  # Complete message history
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
```

### 3. Session States
- **ACTIVE**: Escalated but no agent assigned yet
- **ASSIGNED**: Human agent has accepted the ticket
- **CLOSED**: Conversation completed and archived

## Database Schema (Supabase)

### Table: `conversation_sessions`
```sql
CREATE TABLE conversation_sessions (
    session_id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    thread_ts TEXT,
    state TEXT NOT NULL CHECK (state IN ('active', 'assigned', 'closed')),
    assigned_to TEXT,
    escalated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    escalation_reason TEXT NOT NULL,
    history JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_conversation_sessions_user_id ON conversation_sessions(user_id);
CREATE INDEX idx_conversation_sessions_state ON conversation_sessions(state);
CREATE INDEX idx_conversation_sessions_thread_ts ON conversation_sessions(thread_ts);
```

## How Messages Are Stored

### 1. Message Structure in History
Each message in the `history` array follows this structure:
```python
{
    'sender': str,           # 'User', 'AI Agent', or 'Agent (name)'
    'content': str,          # The actual message content
    'timestamp': str,        # ISO format timestamp
    'message_type': str,     # 'user_message', 'ai_response', 'agent_reply', etc.
    'platform': str,         # 'Chainlit', 'Slack', 'Website'
    'confidence_score': float,  # AI confidence (if applicable)
    'agent_name': str,       # Which AI agent generated it (if applicable)
    'metadata': dict         # Additional context
}
```

### 2. Storage Workflow

**When User Sends Message:**
```python
await session_manager.add_message_to_session(
    session_id=session.session_id,
    message={
        'sender': 'User',
        'content': user_message,
        'timestamp': datetime.now().isoformat(),
        'message_type': 'user_message',
        'platform': 'Chainlit'
    }
)
```

**When AI Responds:**
```python
await session_manager.add_message_to_session(
    session_id=session.session_id,
    message={
        'sender': 'AI Agent',
        'content': ai_response,
        'timestamp': datetime.now().isoformat(),
        'message_type': 'ai_response',
        'agent_name': 'enhanced_rag_agent',
        'confidence_score': 0.85
    }
)
```

**When Human Agent Replies:**
```python
await session_manager.add_message_to_session(
    session_id=session.session_id,
    message={
        'sender': f'Agent ({agent_name})',
        'content': agent_message,
        'timestamp': datetime.now().isoformat(),
        'message_type': 'agent_reply',
        'platform': 'Slack'
    }
)
```

## Key Operations

### 1. Session Creation
```python
# When escalation occurs
session = await session_manager.create_session(
    user_id='chainlit_user123',
    channel_id='chainlit_channel',
    escalation_reason='Low confidence RAG response',
    history=conversation_history  # Previous AI conversation
)
```

### 2. Session Retrieval
```python
# Get active session for user
active_session = await session_manager.get_user_active_session(user_id)

# Get specific session
session = await session_manager.get_session(session_id)
```

### 3. Agent Assignment
```python
# When agent clicks "Accept Ticket"
success = await session_manager.assign_session(
    session_id=session_id,
    agent_slack_id='U1234567',
    thread_ts='1699123456.789'
)
```

### 4. Session Closure
```python
# When conversation ends
success = await session_manager.close_session(session_id)
```

## Data Flow Example

### Complete Escalation Flow:
1. **User asks question in Chainlit** → Message stored in memory
2. **AI confidence too low** → Triggers escalation
3. **ResponderAgent creates session**:
   ```python
   session = ConversationSession(
       session_id='a83cfbae-b308-40a4-a580-64b04a797f8a',
       user_id='chainlit_olaboyefavour52@gmail.com',
       channel_id='chainlit_1754877871.089597',
       state=SessionState.ACTIVE,
       escalation_reason='Low confidence score (0.00)',
       history=[
           {
               'sender': 'User',
               'content': 'Where is your office?',
               'timestamp': '2025-08-11T03:04:54',
               'platform': 'Chainlit'
           },
           {
               'sender': 'AI Agent', 
               'content': 'Based on retrieved docs...',
               'confidence_score': 0.0,
               'agent_name': 'enhanced_rag_agent'
           }
       ]
   )
   ```

4. **SlackThreadManager creates Slack thread** with buttons
5. **Human agent clicks "Accept Ticket"**:
   - Session state → ASSIGNED
   - `assigned_to` set to agent's Slack ID
   - Slack thread updated

6. **Bidirectional messaging**:
   - User follow-up → Added to session history → Posted to Slack thread
   - Agent reply in Slack → Added to session history → Sent to user

7. **Agent clicks "Close Ticket"**:
   - Session state → CLOSED
   - Thread updated with closed status

## Performance & Scalability

### Database Optimizations:
- **Indexed queries**: User ID, state, and thread timestamp lookups
- **JSON operations**: Efficient JSONB append operations for history
- **Connection pooling**: Supabase handles connection management

### Memory Management:
- **History limits**: Only last N messages kept in active memory
- **Lazy loading**: Full history loaded only when needed
- **Efficient updates**: Incremental history updates, not full rewrites

### Example Query Performance:
```sql
-- Fast user lookup (indexed)
SELECT * FROM conversation_sessions 
WHERE user_id = 'chainlit_user123' 
AND state IN ('active', 'assigned')
ORDER BY escalated_at DESC LIMIT 1;

-- Efficient history append (JSONB)
UPDATE conversation_sessions 
SET history = history || '[{"sender": "User", "content": "Follow up"}]'
WHERE session_id = 'uuid-here';
```

## Integration Points

### 1. Chainlit Integration
- **Platform detection**: `chainlit_` prefix in user/channel IDs
- **Message forwarding**: ResponderAgent forwards messages to Chainlit callback
- **Session display**: User can see their session status and ID

### 2. Slack Integration  
- **Thread management**: Each session maps to a Slack thread
- **Button interactions**: Accept/Close ticket updates session state
- **Message routing**: Thread replies forwarded to user platform

### 3. Multi-Platform Support
- **Platform-agnostic storage**: Sessions work across Chainlit, Slack, Web
- **Unified history**: All messages stored in same format regardless of platform
- **Context preservation**: Full conversation history available to agents

## Monitoring & Analytics

### Session Statistics:
```python
stats = await session_manager.get_session_stats()
# Returns: {
#     'total': 156,
#     'active': 12,
#     'assigned': 8,
#     'closed': 136
# }
```

### Health Monitoring:
```python
health = await responder_agent.health_check()
# Returns: {
#     'session_manager': True,
#     'thread_manager': True,  
#     'supabase_connection': True
# }
```

## Error Handling & Recovery

### Connection Failures:
- **Graceful degradation**: System continues without session persistence
- **Retry logic**: Automatic reconnection attempts
- **Fallback responses**: Generic escalation messages if session creation fails

### Data Consistency:
- **Atomic operations**: Session creation and updates are transactional
- **Conflict resolution**: Duplicate session prevention
- **State validation**: Ensures valid state transitions only

## Security Considerations

### Data Protection:
- **No sensitive data**: Only conversation content and metadata stored
- **Access control**: Supabase Row Level Security (RLS) policies
- **Audit trail**: All session operations logged

### Privacy Compliance:
- **Data retention**: Configurable session cleanup policies
- **User control**: Sessions can be closed/deleted on request
- **Minimal storage**: Only necessary conversation data retained

This session system provides **enterprise-grade conversation management** with full audit trails, agent assignment workflows, and seamless multi-platform integration! 🚀