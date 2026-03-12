#!/bin/bash
# Sync source changes into the existing app bundle without a full rebuild.
# Builds the React frontend, then copies backend + static assets into the bundle.

set -e

BUNDLE="dist/Document Search.app/Contents/Resources/lib/python3.12/backend"
SRC="backend"

echo "Building React frontend..."
(cd frontend && npm run build)
echo "  Frontend built → backend/static/"

echo "Syncing source → bundle..."

cp "$SRC/app.py"                  "$BUNDLE/app.py"
cp "$SRC/indexer.py"              "$BUNDLE/indexer.py"
cp "$SRC/database.py"             "$BUNDLE/database.py"

# Sync Vite build output (index.html + assets/)
BUNDLE_STATIC="$BUNDLE/static"
mkdir -p "$BUNDLE_STATIC/assets"
cp "$SRC/static/index.html"       "$BUNDLE_STATIC/index.html"
rsync -a --delete "$SRC/static/assets/" "$BUNDLE_STATIC/assets/"
echo "  Synced static assets."

# Ensure sqlite3 stdlib package + compiled extension are present (py2app omits them)
PYLIB="dist/Document Search.app/Contents/Resources/lib/python3.12"
DYNLOAD="$PYLIB/lib-dynload"
SQLITE_SRC=$(python3 -c "import _sqlite3; print(_sqlite3.__file__)" 2>/dev/null)
if [ -n "$SQLITE_SRC" ] && [ ! -f "$DYNLOAD/_sqlite3.so" ]; then
    cp "$SQLITE_SRC" "$DYNLOAD/_sqlite3.so"
    echo "  Copied _sqlite3.so into bundle."
fi
SQLITE_PKG=$(python3 -c "import sqlite3, os; print(os.path.dirname(sqlite3.__file__))" 2>/dev/null)
if [ -n "$SQLITE_PKG" ] && [ ! -d "$PYLIB/sqlite3" ]; then
    cp -r "$SQLITE_PKG" "$PYLIB/sqlite3"
    echo "  Copied sqlite3 package into bundle."
fi
cp ".env"                         "dist/Document Search.app/Contents/Resources/.env"
cp "app_launcher.py"              "dist/Document Search.app/Contents/Resources/app_launcher.py"

# Clear cached bytecode so Python picks up the new source
rm -f "$BUNDLE/__pycache__/app"*.pyc \
      "$BUNDLE/__pycache__/indexer"*.pyc \
      "$BUNDLE/__pycache__/database"*.pyc

echo "Done. Relaunch the app to see changes."
