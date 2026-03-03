#!/usr/bin/env python3
"""
Launcher script for Document Search macOS app.
Starts the Flask server and opens it in the default browser.
"""
import os
import sys
import webbrowser
import time
from pathlib import Path

# Get the app bundle directory
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # Running as bundled app (py2app)
    app_dir = Path(sys.argv[0]).parent.parent.parent / 'Resources'
    backend_dir = app_dir / 'backend'
    os.chdir(app_dir)
else:
    # Running from source
    app_dir = Path(__file__).parent
    backend_dir = app_dir / 'backend'
    os.chdir(app_dir)

# Add backend to path
sys.path.insert(0, str(backend_dir.parent))

# Import Flask app
from backend.app import app

def launch():
    """Start the Flask server and open the browser."""
    print(f"Starting Document Search server...")
    print(f"App directory: {app_dir}")
    
    # determine port (allow override via PORT env var)
    port = int(os.getenv('PORT', 5000))

    # Start the Flask server in a background thread
    import threading
    server_thread = threading.Thread(
        target=lambda: app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False),
        daemon=True
    )
    server_thread.start()
    
    # Give the server a moment to start
    time.sleep(2)
    
    # Open in default browser
    webbrowser.open(f'http://127.0.0.1:{port}')
    print("Opened Document Search in your browser.")
    
    # Keep the thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down Document Search...")
        sys.exit(0)

if __name__ == '__main__':
    launch()
