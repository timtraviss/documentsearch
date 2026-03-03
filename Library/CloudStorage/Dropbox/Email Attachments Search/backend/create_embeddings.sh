#!/bin/bash
# Run this script to create embeddings for semantic search
# Note: requires OPENAI_API_KEY to be set in .env

cd "$(dirname "$0")"
source ../venv/bin/activate
python embeddings.py
