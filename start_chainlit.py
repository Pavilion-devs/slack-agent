#!/usr/bin/env python3
"""
Quick launcher for the Chainlit interface.
Starts the Delve LangGraph Workflow Tester with proper configuration.
"""

import subprocess
import sys
import os
from pathlib import Path

def main():
    """Launch the Chainlit interface."""
    print("🚀 Starting Delve LangGraph Workflow Tester...")
    print("=" * 50)
    
    # Ensure we're in the right directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Check if chainlit is installed
    try:
        import chainlit
        print(f"✅ Chainlit found (version: {chainlit.__version__})")
    except ImportError:
        print("❌ Chainlit not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "chainlit>=1.0.0"])
        print("✅ Chainlit installed successfully!")
    
    print("\n🎯 Features of this interface:")
    print("- Test all LangGraph workflow routing")
    print("- Validate intent detection accuracy") 
    print("- Monitor processing performance")
    print("- Verify disambiguation logic")
    
    print(f"\n📂 Starting from: {script_dir}")
    print("🌐 Interface will be available at: http://localhost:8000")
    print("⚡ Auto-reload enabled for development")
    print("\n" + "=" * 50)
    
    try:
        # Start Chainlit with auto-reload
        subprocess.run([
            "chainlit", "run", "chainlit_app.py", 
            "-w",  # Watch for file changes
            "--host", "0.0.0.0",  # Allow external connections
            "--port", "8000"
        ])
    except KeyboardInterrupt:
        print("\n\n👋 Chainlit interface stopped.")
    except Exception as e:
        print(f"\n❌ Error starting Chainlit: {e}")
        print("💡 Try running manually: chainlit run chainlit_app.py -w")

if __name__ == "__main__":
    main()