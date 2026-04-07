# Security Review Log

## 2026-04-07 — full codebase review (post path-traversal fix)

**Result:** PASS WITH NOTES
**Reviewed by:** Bob (Claude Code agent)
**Summary:** Full review of current main branch. No blockers. `_safe_path()` verified via live test — all traversal attempts correctly blocked. One warning: `rename_tag` and `tag_values` routes use f-string SQL column interpolation, safe today due to allowlist validation but a pattern to clean up. `str(e)` in the 500 handler can still leak OS error messages including paths — low risk for local app. No XSS vectors, no secrets in frontend, no injection vectors found.

## 2026-04-07 — delete feature + company filter + amount formatting

**Result:** PASS WITH NOTES (blocker fixed inline)
**Reviewed by:** Bob (Claude Code agent)
**Summary:** Reviewed delete document endpoint, company filter backend fix, and amount formatting changes. Found a path traversal vulnerability on both the DELETE /document and GET /pdf endpoints — `os.path.join` does not neutralise `../` sequences, allowing requests to escape PDF_FOLDER. Fixed by adding `_safe_path()` containment check to both routes. Also removed internal filepath from 500 error responses in serve_pdf. All SQLite operations use parameterised queries. No secrets exposed. Frontend renders snippets as plain text — no XSS vectors.
