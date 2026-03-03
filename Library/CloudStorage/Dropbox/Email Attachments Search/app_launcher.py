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
    try:
        print(f"Starting Document Search server...")
        print(f"App directory: {app_dir}")
        
        # determine port (prefer value from PORT env but fall back if unavailable)
        def _find_free(preferred):
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                s.bind(('127.0.0.1', preferred))
                return s.getsockname()[1]
            except OSError:
                # preferred port is busy, ask OS for any free port
                s.bind(('127.0.0.1', 0))
                return s.getsockname()[1]
            finally:
                s.close()

        env_port = os.getenv('PORT')
        try:
            candidate = int(env_port) if env_port else 5000
        except ValueError:
            candidate = 5000
        port = _find_free(candidate)
        if port != candidate:
            print(f"Port {candidate} unavailable, using {port} instead.")

        # Start the Flask server in a background thread
        import threading
        def run_server():
            try:
                app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False)
            except Exception as e:
                # log failure to stderr and exit so py2app doesn't show generic error page
                print(f"Server failed to start: {e}")
                sys.exit(1)

        server_thread = threading.Thread(
            target=run_server,
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
    except Exception as exc:
        # write crash info to a log next to the resources
        try:
            logpath = Path(app_dir) / 'error.log'
            with open(logpath, 'a') as f:
                import traceback
                f.write('--- launcher exception ---\n')
                traceback.print_exc(file=f)
        except Exception:
            pass
        # re-raise to let py2app show its debugging URL as well
        raise

if __name__ == '__main__':
    launch()
