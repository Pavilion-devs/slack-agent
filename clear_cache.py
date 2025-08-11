#!/usr/bin/env python3
"""
Cache Clearing Script for RAG System

This script clears the fast cache in the Enhanced RAG Agent to force
real knowledge retrieval and test conversation memory properly.
"""

import os
import sys
from typing import Dict, Any

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def clear_fast_cache():
    """Clear the fast cache by modifying the enhanced_rag_agent.py file."""
    
    file_path = os.path.join('src', 'agents', 'enhanced_rag_agent.py')
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False
    
    try:
        print("🧹 Clearing RAG Agent fast cache...")
        
        # Read the file
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Find the fast_cache initialization and replace with empty dict
        lines = content.split('\n')
        new_lines = []
        in_cache_block = False
        
        for i, line in enumerate(lines):
            if '# Fast-path cache for common queries' in line:
                new_lines.append(line)
                new_lines.append('        self.fast_cache = {}  # CACHE CLEARED - Will use real RAG retrieval')
                in_cache_block = True
                continue
            
            if in_cache_block:
                # Skip lines until we find the end of the cache dict
                if line.strip() == '}':
                    in_cache_block = False
                    continue
                elif line.strip().startswith('"') or line.strip().startswith('}'):
                    continue
                else:
                    # End of cache block, add this line normally
                    in_cache_block = False
                    new_lines.append(line)
            else:
                new_lines.append(line)
        
        # Write the modified content back
        modified_content = '\n'.join(new_lines)
        with open(file_path, 'w') as f:
            f.write(modified_content)
        
        print("✅ Fast cache cleared successfully!")
        print("📋 Cache status: DISABLED - All queries will use real RAG retrieval")
        print("🧠 Conversation context will now be properly processed")
        print("\n🎯 You can now test:")
        print("   1. 'I work at a startup with 25 employees'")
        print("   2. 'What's your pricing for my company size?'")
        print("   → Should reference the 25 employees context")
        
        return True
        
    except Exception as e:
        print(f"❌ Error clearing cache: {e}")
        return False

def restore_fast_cache():
    """Restore the original fast cache (for future use)."""
    print("\n💡 To restore the cache later, you can manually add back the cache entries")
    print("   or restore from git if you have version control.")

def main():
    """Main function."""
    print("🚀 RAG System Cache Cleaner")
    print("=" * 40)
    print("This script will clear the fast cache to enable proper")
    print("conversation context processing and memory testing.")
    print()
    
    # Confirm action
    confirm = input("🤔 Clear the fast cache? (y/N): ").strip().lower()
    
    if confirm in ['y', 'yes']:
        success = clear_fast_cache()
        
        if success:
            print("\n🎉 Cache clearing completed!")
            print("\n📝 Next Steps:")
            print("1. Restart Chainlit: python chainlit_app.py")
            print("2. Test contextual queries:")
            print("   → 'I work at a startup with 25 employees'")
            print("   → 'What's your pricing for my company size?'")
            print("3. Or run standalone test: python test_rag_standalone.py")
            print("\n✨ Memory and context should now work properly!")
        else:
            print("\n❌ Cache clearing failed. Please check the error above.")
    else:
        print("❌ Cache clearing cancelled.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)