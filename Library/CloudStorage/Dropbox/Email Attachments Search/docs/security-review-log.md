# Security Review Log

## 2026-04-07 — delete feature + company filter + amount formatting

**Result:** PASS WITH NOTES (blocker fixed inline)
**Reviewed by:** Bob (Claude Code agent)
**Summary:** Reviewed delete document endpoint, company filter backend fix, and amount formatting changes. Found a path traversal vulnerability on both the DELETE /document and GET /pdf endpoints — `os.path.join` does not neutralise `../` sequences, allowing requests to escape PDF_FOLDER. Fixed by adding `_safe_path()` containment check to both routes. Also removed internal filepath from 500 error responses in serve_pdf. All SQLite operations use parameterised queries. No secrets exposed. Frontend renders snippets as plain text — no XSS vectors.
