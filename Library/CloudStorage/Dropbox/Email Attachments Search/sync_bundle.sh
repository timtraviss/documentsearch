#!/bin/bash
# Sync source changes into the existing app bundle without a full rebuild.
# Run this after editing backend/app.py or backend/templates/*.html

set -e

BUNDLE="dist/Document Search.app/Contents/Resources/lib/python3.12/backend"
SRC="backend"

echo "Syncing source → bundle..."

cp "$SRC/app.py"                  "$BUNDLE/app.py"
cp "$SRC/indexer.py"              "$BUNDLE/indexer.py"
cp "$SRC/templates/search.html"   "$BUNDLE/templates/search.html"
cp "$SRC/static/pdf.min.js"       "$BUNDLE/static/pdf.min.js"
cp "$SRC/static/pdf.worker.min.js" "$BUNDLE/static/pdf.worker.min.js"
cp "app_launcher.py"              "dist/Document Search.app/Contents/Resources/app_launcher.py"

# Clear cached bytecode so Python picks up the new source
rm -f "$BUNDLE/__pycache__/app"*.pyc "$BUNDLE/__pycache__/indexer"*.pyc

echo "Done. Relaunch the app to see changes."
