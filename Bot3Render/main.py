"""
Main entry point for the Aerial Threat Tracking System
Runs both the Flask web server and Telegram Userbot in parallel
"""
import threading
import os
import sys
from server import app

def run_flask():
    """Run Flask server on port 3000"""
    port = int(os.getenv('PORT', 3000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def main():
    """Start both Flask server and Telegram Userbot"""
    print("=" * 60)
    print("AERIAL THREAT TRACKING SYSTEM (USERBOT)")
    print("=" * 60)
    print("\n🚀 Starting services...")
    
    # Start Flask server in a separate thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("✓ Web server started on port", os.getenv('PORT', 3000))
    
    # Check if Telegram userbot credentials are set
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    
    if not api_id or not api_hash:
        print("\n⚠️  Telegram userbot credentials not configured")
        print("   Web interface will work, but userbot is disabled")
        print("   Set these environment variables to enable:")
        print("   - TELEGRAM_API_ID")
        print("   - TELEGRAM_API_HASH")
        print("   - TELEGRAM_SESSION_STRING")
        print("   - MONITORED_CHANNELS")
        print("\n✓ Web interface available")
        print("=" * 60)
        
        # Keep the main thread alive
        try:
            flask_thread.join()
        except KeyboardInterrupt:
            print("\n👋 Shutting down...")
            sys.exit(0)
    else:
        print("✓ Telegram userbot credentials found")
        print("\n✓ System ready")
        print("=" * 60)
        
        # Import and run userbot only if credentials are present
        try:
            from userbot import run_userbot
            # Run Telegram userbot (blocking)
            run_userbot()
        except Exception as e:
            print(f"\n⚠️  Userbot failed to start: {e}")
            print("   Web interface will continue running")
            print("\n✓ Web interface available")
            print("=" * 60)
            
            # Keep Flask running
            try:
                flask_thread.join()
            except KeyboardInterrupt:
                print("\n👋 Shutting down...")
                sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
