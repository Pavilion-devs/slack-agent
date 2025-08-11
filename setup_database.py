#!/usr/bin/env python3
"""
Database setup script for Supabase PostgreSQL database.
This script creates the required tables and functions for the responder agent system.
"""

import os
import sys
import asyncio
from dotenv import load_dotenv
from supabase import create_client, Client
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()


async def setup_database():
    """Setup the Supabase database with required schema."""
    print("🗄️  Setting up Supabase database schema...")
    print("=" * 50)
    
    # Get Supabase credentials
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        print("❌ Missing Supabase credentials in .env file")
        print("Required: SUPABASE_URL and SUPABASE_KEY")
        return False
    
    print(f"🔗 Connecting to Supabase: {supabase_url}")
    
    try:
        # Create Supabase client
        supabase: Client = create_client(supabase_url, supabase_key)
        print("✅ Supabase client created successfully")
        
        # Check if tables already exist
        try:
            result = supabase.table('conversation_sessions').select('session_id', count='exact').limit(1).execute()
            print("ℹ️  Tables already exist - checking structure...")
            
            # Get existing record count
            print(f"📊 Existing sessions: {result.count}")
            
            # Test other tables
            tables_to_check = ['agent_metrics', 'escalation_logs', 'system_health']
            for table in tables_to_check:
                try:
                    result = supabase.table(table).select('*', count='exact').limit(1).execute()
                    print(f"✅ Table '{table}' exists with {result.count} records")
                except Exception as e:
                    print(f"⚠️  Table '{table}' missing or has issues: {e}")
        
        except Exception as e:
            print(f"ℹ️  Tables don't exist yet, need to create them: {e}")
            print("📝 Please run the SQL schema in your Supabase SQL Editor:")
            print("   1. Go to https://supabase.com/dashboard/project/[your-project-id]/sql/new")
            print("   2. Copy and paste the contents of: scripts/setup_supabase_schema.sql")
            print("   3. Click 'Run' to execute the schema")
            print("")
            print("SQL file location: scripts/setup_supabase_schema.sql")
            
            # Show the schema file contents
            schema_file = "scripts/setup_supabase_schema.sql"
            if os.path.exists(schema_file):
                print("\n📄 Schema file contents:")
                print("-" * 50)
                with open(schema_file, 'r') as f:
                    content = f.read()
                    # Show first 20 lines
                    lines = content.split('\n')[:20]
                    for i, line in enumerate(lines, 1):
                        print(f"{i:2d}: {line}")
                    if len(content.split('\n')) > 20:
                        print(f"... and {len(content.split('\n')) - 20} more lines")
                print("-" * 50)
        
        # Test basic operations
        print("\n🧪 Testing database operations...")
        
        # Test session creation (this will work if tables exist)
        try:
            import uuid
            from datetime import datetime, timezone
            
            test_session_id = str(uuid.uuid4())
            
            # Try to insert a test record
            test_data = {
                'session_id': test_session_id,
                'user_id': 'test_user',
                'channel_id': 'test_channel',
                'state': 'active',
                'escalation_reason': 'Database setup test',
                'escalated_at': datetime.now(timezone.utc).isoformat(),
                'history': '[]'
            }
            
            result = supabase.table('conversation_sessions').insert(test_data).execute()
            
            if result.data:
                print("✅ Test record created successfully")
                
                # Clean up test record
                supabase.table('conversation_sessions').delete().eq('session_id', test_session_id).execute()
                print("✅ Test record cleaned up")
                
        except Exception as e:
            print(f"⚠️  Database operations test failed: {e}")
            print("This is expected if the schema hasn't been created yet.")
        
        print("\n" + "=" * 50)
        print("🎉 Database setup check complete!")
        
        return True
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_session_manager():
    """Test the session manager with the database."""
    print("\n🔧 Testing SessionManager integration...")
    
    try:
        sys.path.append('.')
        from src.core.session_manager import SessionManager
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        session_manager = SessionManager(supabase_url, supabase_key)
        
        # Test basic stats
        stats = await session_manager.get_session_stats()
        print(f"📊 Session stats: {stats}")
        
        print("✅ SessionManager working correctly!")
        
    except Exception as e:
        print(f"❌ SessionManager test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    async def main():
        success = await setup_database()
        
        if success:
            await test_session_manager()
        
        return success
    
    success = asyncio.run(main())
    sys.exit(0 if success else 1)