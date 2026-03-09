#!/usr/bin/env python3
"""
Launcher script for Document Search macOS app.
Starts the Flask server and opens it in a native pywebview window.
"""
import os
import sys
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

# Explicitly load .env from the app_dir before importing Flask app.
# load_dotenv() inside app.py uses a file-relative search which can fail
# in py2app bundles, so we guarantee it here with an absolute path.
try:
    from dotenv import load_dotenv as _load_env
    _load_env(app_dir / '.env', override=False)
except Exception as _e:
    print(f"Warning: could not pre-load .env: {_e}")

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
                app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False, threaded=True)
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
        time.sleep(1.5)

        # Ensure the app appears in the Dock as a regular foreground application.
        # pywebview on macOS can start without a Dock icon unless activation policy
        # is explicitly set to Regular.
        try:
            import AppKit
            ns_app = AppKit.NSApplication.sharedApplication()
            ns_app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyRegular)
            ns_app.activateIgnoringOtherApps_(True)
        except Exception:
            pass

        # Open in a native window via pywebview (must run on main thread)
        import webview
        window = webview.create_window(
            'Document Search',
            f'http://127.0.0.1:{port}',
            width=1280,
            height=860,
            min_size=(800, 600),
        )
        webview.start()
        print("Document Search window closed. Shutting down...")
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
