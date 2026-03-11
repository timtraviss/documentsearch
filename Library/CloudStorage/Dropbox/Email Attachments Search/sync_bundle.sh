#!/bin/bash
# Sync source changes into the existing app bundle without a full rebuild.
# Run this after editing backend/app.py or backend/templates/*.html

set -e

BUNDLE="dist/Document Search.app/Contents/Resources/lib/python3.12/backend"
SRC="backend"

echo "Syncing source → bundle..."

cp "$SRC/app.py"                  "$BUNDLE/app.py"
cp "$SRC/indexer.py"              "$BUNDLE/indexer.py"
cp "$SRC/database.py"             "$BUNDLE/database.py"

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
cp "$SRC/templates/search.html"   "$BUNDLE/templates/search.html"
cp "$SRC/static/pdf.min.js"       "$BUNDLE/static/pdf.min.js"
cp "$SRC/static/pdf.worker.min.js" "$BUNDLE/static/pdf.worker.min.js"
cp "app_launcher.py"              "dist/Document Search.app/Contents/Resources/app_launcher.py"

# Clear cached bytecode so Python picks up the new source
rm -f "$BUNDLE/__pycache__/app"*.pyc \
      "$BUNDLE/__pycache__/indexer"*.pyc \
      "$BUNDLE/__pycache__/database"*.pyc

echo "Done. Relaunch the app to see changes."
