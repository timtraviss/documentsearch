import os
import re
import csv
import io
import json
import socket
import threading
import traceback
from urllib.parse import unquote
from datetime import datetime

from flask import Flask, Response, g, render_template, request, jsonify, send_from_directory
from dotenv import load_dotenv

load_dotenv()

PDF_FOLDER = os.getenv("PDF_FOLDER")

_here = os.path.dirname(os.path.abspath(__file__))
_static = os.path.join(_here, "static")
app = Flask(__name__)

# ---------------------------------------------------------------------------
# Database — initialise schema on startup, one connection per request via g
# ---------------------------------------------------------------------------

import shutil

from backend.database import (
    init_db,
    get_connection as _get_connection,
    get_db_path,
    get_document_count,
    upsert_tag,
    get_tag,
    get_all_tags,
    delete_document,
)

from backend.extraction import (
    extract_company_from_filename,
    extract_company,
    extract_date,
    normalise_amount,
    extract_total_amount,
    extract_invoice_number,
)

init_db()
_DB_PATH = get_db_path()


def get_db():
    """Return the per-request SQLite connection, opening it on first use."""
    if "db" not in g:
        g.db = _get_connection()
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


# ---------------------------------------------------------------------------
# Optional semantic search
# ---------------------------------------------------------------------------

try:
    from embeddings import search as semantic_search
    HAS_EMBEDDINGS = os.path.exists(
        os.path.join(os.path.dirname(__file__), "vector.faiss")
    )
except ImportError:
    HAS_EMBEDDINGS = False

REINDEX_TOKEN = os.getenv("REINDEX_TOKEN")
APP_VERSION = "0.5"

# In-memory status for the background reindex thread
reindex_status = {
    "running": False,
    "logs": [],
    "count": 0,
    "skipped": 0,
    "error": None,
    "obsidian": None,
}

# ---------------------------------------------------------------------------
# Search helpers
# ---------------------------------------------------------------------------

_STOP_WORDS = {
    "a", "an", "the", "at", "in", "on", "of", "for", "to",
    "and", "or", "is", "was", "are", "with", "by", "from",
}


def text_search(conn, q, filter_company="", filter_date="",
                filter_amount="", filter_mode="and"):
    """FTS5-backed keyword search with optional metadata filters.

    Falls back to a LIKE scan if the query contains characters that would
    cause an FTS MatchError (e.g. bare special chars, empty token set).
    filter_mode is "and" (all filters) or "or" (any filter).
    """
    tokens = [t for t in q.lower().split() if t not in _STOP_WORDS] if q else []

    if tokens:
        match_expr = " AND ".join(tokens)
        try:
            rows = conn.execute(
                """
                SELECT d.filename,
                       d.relative_path,
                       d.text,
                       snippet(documents_fts, 1, '', '', '...', 20) AS fts_snippet,
                       COALESCE(t.company, '') AS tagged_company
                FROM documents_fts
                JOIN documents d ON d.id = documents_fts.rowid
                LEFT JOIN tags t ON t.relative_path = d.relative_path
                WHERE documents_fts MATCH ?
                ORDER BY rank
                """,
                (match_expr,),
            ).fetchall()
        except Exception:
            # MatchError fallback — simple LIKE across filename + text
            pattern = f"%{q.lower()}%"
            rows = conn.execute(
                """
                SELECT d.filename, d.relative_path, d.text,
                       substr(d.text, 1, 300) AS fts_snippet,
                       COALESCE(t.company, '') AS tagged_company
                FROM documents d
                LEFT JOIN tags t ON t.relative_path = d.relative_path
                WHERE lower(d.text || ' ' || d.filename) LIKE ?
                """,
                (pattern,),
            ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT d.filename, d.relative_path, d.text,
                   substr(d.text, 1, 300) AS fts_snippet,
                   COALESCE(t.company, '') AS tagged_company
            FROM documents d
            LEFT JOIN tags t ON t.relative_path = d.relative_path
            """
        ).fetchall()

    results = []
    for row in rows:
        text_content = row["text"]
        tagged_company = row["tagged_company"] or ""
        company = tagged_company or extract_company(text_content) or ""
        date = extract_date(text_content) or ""
        amount = extract_total_amount(text_content) or ""

        pass_company = pass_date = pass_amount = True

        if filter_company:
            # Check tagged company first, then fall back to regex-extracted
            pass_company = (
                filter_company in tagged_company.lower()
                or filter_company in (extract_company(text_content) or "").lower()
            )

        if filter_date:
            if len(filter_date) == 4 and filter_date.isdigit():
                pass_date = date.startswith(filter_date)
            else:
                pass_date = filter_date in date

        if filter_amount:
            try:
                if "-" in filter_amount:
                    min_amt, max_amt = map(float, filter_amount.split("-"))
                else:
                    min_amt = max_amt = float(filter_amount)
                amount_num = float(re.sub(r"[^0-9.]", "", amount)) if amount else 0
                pass_amount = min_amt <= amount_num <= max_amt
            except ValueError:
                pass_amount = True

        if filter_mode == "or":
            if not (pass_company or pass_date or pass_amount):
                continue
        else:
            if not (pass_company and pass_date and pass_amount):
                continue

        results.append({
            "filename": row["filename"],
            "path": row["relative_path"],
            "snippet": row["fts_snippet"] or text_content[:300],
            "company": company,
            "date": date,
            "amount": amount,
        })

    return results


def _tag_browse(conn, tag_type, tag_year, tag_untagged):
    """Return results for tag-only browse (no text query)."""
    results = []

    if tag_untagged:
        # Documents with no tag row at all, or with all-blank tag values
        rows = conn.execute(
            """
            SELECT d.filename, d.relative_path, d.text
            FROM documents d
            LEFT JOIN tags t ON t.relative_path = d.relative_path
            WHERE t.relative_path IS NULL
               OR (TRIM(COALESCE(t.type, '')) = ''
               AND TRIM(COALESCE(t.company, '')) = ''
               AND TRIM(COALESCE(t.year, '')) = '')
            """
        ).fetchall()
        for row in rows:
            fname = row["filename"]
            results.append({
                "filename": fname,
                "path": row["relative_path"],
                "snippet": row["text"][:300],
                "company": extract_company_from_filename(fname) or "",
                "date": "",
                "amount": "",
                "tags": {},
            })
    else:
        conditions, params = [], []
        if tag_type:
            conditions.append("LOWER(t.type) = ?")
            params.append(tag_type)
        if tag_year:
            conditions.append("t.year = ?")
            params.append(tag_year)
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        rows = conn.execute(
            f"""
            SELECT d.filename, d.relative_path, d.text,
                   t.type, t.company, t.year, t.amount, t.invoice_number, t.status
            FROM tags t
            JOIN documents d ON d.relative_path = t.relative_path
            {where}
            """,
            params,
        ).fetchall()
        for row in rows:
            tag = {
                "type": row["type"],
                "company": row["company"],
                "year": row["year"],
                "amount": row["amount"],
                "invoice_number": row["invoice_number"],
                "status": row["status"],
            }
            text = row["text"]
            fname = row["filename"]
            results.append({
                "filename": fname,
                "path": row["relative_path"],
                "snippet": text[:300],
                "company": (tag.get("company")
                            or extract_company(text)
                            or extract_company_from_filename(fname)
                            or ""),
                "date": tag.get("year") or extract_date(text) or "",
                "amount": extract_total_amount(text) or "",
                "tags": tag,
            })

    return results


def _attach_tags(conn, results):
    """Batch-fetch tags for a result list and attach them in-place."""
    if not results:
        return
    paths = [r["path"] for r in results]
    placeholders = ",".join("?" * len(paths))
    rows = conn.execute(
        f"SELECT relative_path, type, company, year, amount, invoice_number, status "
        f"FROM tags WHERE relative_path IN ({placeholders})",
        paths,
    ).fetchall()
    tags_map = {
        row["relative_path"]: {
            "type": row["type"],
            "company": row["company"],
            "year": row["year"],
            "amount": row["amount"],
            "invoice_number": row["invoice_number"],
            "status": row["status"],
        }
        for row in rows
    }
    for r in results:
        r["tags"] = tags_map.get(r["path"], {})


def _apply_tag_filters(results, tag_type, tag_year, tag_untagged):
    filtered = []
    for r in results:
        t = r.get("tags", {})
        if tag_type and t.get("type", "").lower() != tag_type:
            continue
        if tag_year and t.get("year", "") != tag_year:
            continue
        if tag_untagged and any(str(v).strip() for v in t.values()):
            continue
        filtered.append(r)
    return filtered


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    index = os.path.join(_static, "index.html")
    if os.path.exists(index):
        return send_from_directory(_static, "index.html")
    # Fallback: legacy Jinja template when React hasn't been built yet
    return render_template(
        "search.html",
        has_embeddings=HAS_EMBEDDINGS,
        reindex_token_present=bool(REINDEX_TOKEN),
        version=APP_VERSION,
    )


@app.route("/assets/<path:filename>")
def react_assets(filename: str):
    """Serve Vite-built JS/CSS assets."""
    return send_from_directory(os.path.join(_static, "assets"), filename)


@app.route("/search")
def search():
    q = request.args.get("q", "").lower()
    search_type = request.args.get("type", "semantic" if HAS_EMBEDDINGS else "text")
    filter_company = request.args.get("company", "").lower()
    filter_date = request.args.get("date", "")
    filter_amount = request.args.get("amount", "")
    filter_mode = request.args.get("mode", "and").lower()
    tag_type = request.args.get("tag_type", "").lower()
    tag_year = request.args.get("tag_year", "")
    tag_untagged = request.args.get("tag_untagged", "").lower() in ("1", "true")

    try:
        limit = min(max(int(request.args.get("limit", 20)), 1), 200)
        offset = max(int(request.args.get("offset", 0)), 0)
    except (ValueError, TypeError):
        limit, offset = 20, 0

    has_query = bool(q or filter_company or filter_date or filter_amount)
    has_tag_filters = bool(tag_type or tag_year or tag_untagged)

    if not has_query and not has_tag_filters:
        return jsonify([])

    conn = get_db()

    if not has_query and has_tag_filters:
        results = _tag_browse(conn, tag_type, tag_year, tag_untagged)
        return jsonify(results[offset:offset + limit])

    # Text or semantic search
    if search_type == "semantic" and HAS_EMBEDDINGS:
        try:
            top_k = 50 if has_tag_filters else 10
            results = semantic_search(q, top_k=top_k)
            for r in results:
                row = conn.execute(
                    "SELECT text FROM documents WHERE relative_path = ?",
                    (r.get("path", ""),),
                ).fetchone()
                text = row["text"] if row else ""
                r["company"] = extract_company(text) or ""
                r["date"] = extract_date(text) or ""
                r["amount"] = extract_total_amount(text) or ""
        except Exception as e:
            print(f"Semantic search error: {e}")
            results = text_search(
                conn, q, filter_company, filter_date, filter_amount, filter_mode
            )
    else:
        results = text_search(
            conn, q, filter_company, filter_date, filter_amount, filter_mode
        )

    _attach_tags(conn, results)

    if has_tag_filters:
        results = _apply_tag_filters(results, tag_type, tag_year, tag_untagged)

    return jsonify(results[offset:offset + limit])


@app.route("/reindex", methods=["POST"])
def reindex():
    """Start a background reindex job."""
    if REINDEX_TOKEN:
        provided = (request.headers.get("X-Reindex-Token")
                    or (request.json or {}).get("token"))
        if not provided or provided != REINDEX_TOKEN:
            return jsonify({"status": "error", "error": "invalid or missing token"}), 403

    if reindex_status["running"]:
        return jsonify({"status": "error", "error": "reindex already running"}), 409

    body = request.get_json(silent=True) or {}
    incremental = bool(body.get("incremental", False))

    def _log(msg):
        reindex_status["logs"].append(msg)

    def worker(incremental=incremental):
        # Background thread — cannot use Flask g; open its own DB connection.
        conn = None
        try:
            reindex_status["running"] = True
            reindex_status["logs"] = []
            reindex_status["count"] = 0
            reindex_status["skipped"] = 0
            reindex_status["error"] = None
            reindex_status["obsidian"] = None

            mode = "incremental" if incremental else "full"
            _log(f"Starting {mode} reindex...")

            from backend.indexer import scan_pdfs, save_index_to_db
            from backend.database import get_connection as _conn

            folder = PDF_FOLDER or os.getenv("PDF_FOLDER")
            if not folder or not os.path.isdir(folder):
                reindex_status["error"] = "PDF_FOLDER not configured or not found"
                _log(reindex_status["error"])
                return

            _log(f"Scanning folder: {folder}")
            conn = _conn()

            def progress_cb(path, idx, total, skipped=False):
                name = path.split("/")[-1]
                if skipped:
                    reindex_status["skipped"] += 1
                    _log(f"Unchanged ({idx}/{total}): {name}")
                else:
                    _log(f"Indexed ({idx}/{total}): {name}")

            docs = scan_pdfs(
                folder,
                progress_callback=progress_cb,
                db_conn=conn,
            )
            _log(f"Saving index ({len(docs)} documents, "
                 f"{reindex_status['skipped']} unchanged)")

            save_index_to_db(conn, docs, incremental=incremental)

            reindex_status["count"] = len(docs)
            _log("Reindex complete")

            # --- Obsidian sidecar export ---
            obsidian_vault = os.getenv("OBSIDIAN_VAULT", "").strip()
            export_mode = os.getenv("OBSIDIAN_EXPORT_MODE", "regex").strip()
            if obsidian_vault and os.path.isdir(obsidian_vault):
                from backend.obsidian import export_to_obsidian
                wrote_count = 0
                skipped_count = 0
                _log(f"Exporting sidecars to {obsidian_vault} (mode={export_mode})...")
                for doc in docs:
                    try:
                        wrote, dest = export_to_obsidian(doc, obsidian_vault, mode=export_mode)
                        if wrote:
                            wrote_count += 1
                        else:
                            skipped_count += 1
                    except Exception as e:
                        _log(f"Sidecar error ({doc.get('filename', '?')}): {e}")
                reindex_status["obsidian"] = {"wrote": wrote_count, "skipped": skipped_count}
                _log(f"Sidecars: {wrote_count} written, {skipped_count} already existed")
            elif obsidian_vault:
                _log(f"OBSIDIAN_VAULT not found at {obsidian_vault} — skipping export")
            else:
                _log("OBSIDIAN_VAULT not set — skipping sidecar export")

        except Exception as e:
            reindex_status["error"] = str(e)
            _log(f"Error: {e}")
        finally:
            reindex_status["running"] = False
            if conn:
                conn.close()

    threading.Thread(target=worker, daemon=True).start()
    return jsonify({"status": "ok", "message": "reindex started", "incremental": incremental})


@app.route("/reindex/status")
def reindex_status_api():
    logs = reindex_status.get("logs", [])[-200:]
    return jsonify({
        "running": reindex_status.get("running", False),
        "logs": logs,
        "count": reindex_status.get("count", 0),
        "skipped": reindex_status.get("skipped", 0),
        "error": reindex_status.get("error"),
        "obsidian": reindex_status.get("obsidian"),
    })


@app.route("/tags/<path:filename>", methods=["GET"])
def get_doc_tags(filename):
    """Return saved tags for a document; auto-populate from extraction if not set."""
    conn = get_db()
    tag = get_tag(conn, filename)
    if not tag:
        row = conn.execute(
            "SELECT filename, text FROM documents WHERE relative_path = ? LIMIT 1",
            (filename,),
        ).fetchone()
        if row:
            text = row["text"]
            fname = row["filename"]
            date = extract_date(text) or ""
            tag = {
                "type": "",
                "company": (extract_company(text)
                            or extract_company_from_filename(fname)
                            or ""),
                "year": date[:4] if date else "",
                "auto": True,
            }
        else:
            tag = {}
    return jsonify(tag)


@app.route("/tags/<path:filename>", methods=["POST"])
def save_doc_tags(filename):
    """Save user-applied tags for a document."""
    data = request.get_json(force=True) or {}
    fields = {
        "type": data.get("type", ""),
        "company": data.get("company", ""),
        "year": str(data.get("year", "")),
        "amount": normalise_amount(data.get("amount", "")),
        "invoice_number": data.get("invoice_number", ""),
        "status": data.get("status", ""),
    }
    conn = get_db()
    upsert_tag(conn, filename, fields)
    conn.commit()
    return jsonify({"status": "ok"})


def _safe_path(base: str, filename: str):
    """Return resolved filepath if it stays within base, else None."""
    resolved = os.path.abspath(os.path.join(base, filename))
    if not resolved.startswith(os.path.abspath(base) + os.sep):
        return None
    return resolved


@app.route("/pdf/<path:filename>")
def serve_pdf(filename):
    """Serve a PDF file inline."""
    filename = unquote(filename)
    if not PDF_FOLDER:
        return jsonify({"error": "PDF_FOLDER not configured — check .env"}), 503
    filepath = _safe_path(PDF_FOLDER, filename)
    if filepath is None:
        return jsonify({"error": "invalid path"}), 400
    try:
        with open(filepath, "rb") as f:
            data = f.read()
        return Response(data, mimetype="application/pdf",
                        headers={"Content-Disposition": "inline"})
    except FileNotFoundError:
        return jsonify({"error": "file not found"}), 404
    except PermissionError:
        return jsonify({
            "error": "permission_denied",
            "message": (
                "macOS has blocked access to this file. Grant Full Disk Access to "
                "Document Search in System Settings → Privacy & Security → Full Disk Access."
            ),
        }), 403
    except Exception as e:
        try:
            log = os.path.join(os.path.dirname(__file__), "pdf_error.log")
            with open(log, "a") as lf:
                lf.write(f"path={filepath}\nexc={type(e).__name__}: {e}\n")
                traceback.print_exc(file=lf)
                lf.write("---\n")
        except Exception:
            pass
        return jsonify({"error": str(e), "type": type(e).__name__}), 500


@app.route("/document/<path:filename>", methods=["DELETE"])
def delete_document_route(filename):
    """Move a document to PDF_FOLDER/Deleted/ with a timestamp prefix, then remove from index."""
    filename = unquote(filename)
    if not PDF_FOLDER:
        return jsonify({"error": "PDF_FOLDER not configured — check .env"}), 503
    filepath = _safe_path(PDF_FOLDER, filename)
    if filepath is None:
        return jsonify({"error": "invalid path"}), 400
    try:
        deleted_dir = os.path.join(PDF_FOLDER, "Deleted")
        os.makedirs(deleted_dir, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        dest_name = f"{timestamp}_{os.path.basename(filename)}"
        shutil.move(filepath, os.path.join(deleted_dir, dest_name))
    except FileNotFoundError:
        pass  # already gone — still clean up the index
    except PermissionError:
        return jsonify({"error": "permission_denied"}), 403
    conn = get_db()
    delete_document(conn, filename)
    return jsonify({"status": "ok"})


@app.route("/companies")
def get_companies():
    """Return sorted list of unique company names from tags."""
    conn = get_db()
    rows = conn.execute(
        "SELECT DISTINCT TRIM(company) AS company FROM tags "
        "WHERE TRIM(company) != '' ORDER BY company"
    ).fetchall()
    return jsonify([row["company"] for row in rows])


@app.route("/bulk_tags", methods=["POST"])
def bulk_tags():
    """Apply tags to multiple documents at once; only overwrites non-empty fields."""
    data = request.get_json(force=True) or {}
    paths = data.get("paths", [])
    if not paths:
        return jsonify({"status": "error", "error": "no paths provided"}), 400
    updates = {k: v for k, v in {
        "type": data.get("type", ""),
        "company": data.get("company", ""),
        "year": str(data.get("year", "")),
    }.items() if v}
    if not updates:
        return jsonify({"status": "error", "error": "no tag values provided"}), 400

    conn = get_db()
    for path in paths:
        existing = get_tag(conn, path) or {}
        upsert_tag(conn, path, {**existing, **updates})
    conn.commit()
    return jsonify({"status": "ok", "updated": len(paths)})


@app.route("/tag_values")
def tag_values():
    """Return unique values for type/company/year with counts."""
    conn = get_db()
    result = {}
    for field in ("type", "company", "year"):
        rows = conn.execute(
            f"SELECT {field} AS val, COUNT(*) AS cnt FROM tags "
            f"WHERE TRIM({field}) != '' GROUP BY {field} ORDER BY {field}"
        ).fetchall()
        result[field] = {row["val"]: row["cnt"] for row in rows}
    return jsonify(result)


@app.route("/rename_tag", methods=["POST"])
def rename_tag():
    """Rename a tag value across all documents."""
    data = request.get_json(force=True) or {}
    field = data.get("field", "")
    old_value = data.get("old_value", "").strip()
    new_value = data.get("new_value", "").strip()
    if field not in ("type", "company", "year") or not old_value:
        return jsonify({"status": "error", "error": "invalid field or value"}), 400

    conn = get_db()
    cursor = conn.execute(
        f"UPDATE tags SET {field} = ?, updated_at = datetime('now') "
        f"WHERE TRIM({field}) = ?",
        (new_value, old_value),
    )
    conn.commit()
    return jsonify({"status": "ok", "updated": cursor.rowcount})


@app.route("/stats")
def stats():
    """Return document count and last-indexed timestamp."""
    conn = get_db()
    doc_count = get_document_count(conn)
    # Use the DB file's mtime as the last-indexed timestamp
    last_indexed = None
    if os.path.exists(_DB_PATH):
        mtime = os.path.getmtime(_DB_PATH)
        last_indexed = datetime.fromtimestamp(mtime).strftime("%-d %b %Y, %H:%M")
    return jsonify({"doc_count": doc_count, "last_indexed": last_indexed})


@app.route("/stats/breakdown")
def stats_breakdown():
    """Return tag value counts grouped by type, company, and year."""
    conn = get_db()
    doc_count = get_document_count(conn)

    def _counts(field):
        rows = conn.execute(
            f"SELECT {field} AS val, COUNT(*) AS cnt FROM tags "
            f"WHERE TRIM({field}) != '' GROUP BY {field} ORDER BY cnt DESC"
        ).fetchall()
        return {row["val"]: row["cnt"] for row in rows}

    tagged = conn.execute(
        "SELECT COUNT(*) FROM tags "
        "WHERE TRIM(type) != '' OR TRIM(company) != '' OR TRIM(year) != ''"
    ).fetchone()[0]

    return jsonify({
        "total_docs": doc_count,
        "tagged_docs": tagged,
        "by_type": _counts("type"),
        "by_company": _counts("company"),
        "by_year": _counts("year"),
    })


@app.route("/export/csv")
def export_csv():
    """Export matching results with tags as a CSV file."""
    q = request.args.get("q", "").lower()
    filter_company = request.args.get("company", "").lower()
    filter_date = request.args.get("date", "")
    filter_amount = request.args.get("amount", "")
    filter_mode = request.args.get("mode", "and").lower()
    tag_type = request.args.get("tag_type", "").lower()
    tag_year = request.args.get("tag_year", "")
    tag_untagged = request.args.get("tag_untagged", "").lower() in ("1", "true")

    has_query = bool(q or filter_company or filter_date or filter_amount)
    has_tag_filters = bool(tag_type or tag_year or tag_untagged)

    conn = get_db()

    if has_query:
        results = text_search(conn, q, filter_company, filter_date,
                               filter_amount, filter_mode)
        _attach_tags(conn, results)
    else:
        rows = conn.execute(
            """
            SELECT d.filename, d.relative_path, d.text,
                   COALESCE(t.type, '') AS type,
                   COALESCE(t.company, '') AS company,
                   COALESCE(t.year, '') AS year,
                   COALESCE(t.amount, '') AS amount,
                   COALESCE(t.invoice_number, '') AS invoice_number,
                   COALESCE(t.status, '') AS status
            FROM documents d
            LEFT JOIN tags t ON t.relative_path = d.relative_path
            """
        ).fetchall()
        results = []
        for row in rows:
            text = row["text"]
            fname = row["filename"]
            tag = {
                "type": row["type"],
                "company": row["company"],
                "year": row["year"],
                "amount": row["amount"],
                "invoice_number": row["invoice_number"],
                "status": row["status"],
            }
            results.append({
                "filename": fname,
                "path": row["relative_path"],
                "snippet": text[:300],
                "company": tag["company"] or extract_company(text) or extract_company_from_filename(fname) or "",
                "date": tag["year"] or extract_date(text) or "",
                "amount": extract_total_amount(text) or "",
                "tags": tag,
            })

    if has_tag_filters:
        results = _apply_tag_filters(results, tag_type, tag_year, tag_untagged)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Filename", "Company", "Type", "Year", "Amount",
                     "Invoice Number", "Path"])
    for r in results:
        tag = r.get("tags", {})
        writer.writerow([
            r.get("filename", ""),
            tag.get("company") or r.get("company", ""),
            tag.get("type", ""),
            tag.get("year", "") or r.get("date", ""),
            tag.get("amount") or r.get("amount", ""),
            tag.get("invoice_number", ""),
            r.get("path", ""),
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=documents_export.csv"},
    )


@app.route("/debug")
def debug_info():
    """Diagnostic endpoint."""
    import glob as _glob
    sample = []
    if PDF_FOLDER and os.path.isdir(PDF_FOLDER):
        sample = [os.path.basename(p)
                  for p in _glob.glob(os.path.join(PDF_FOLDER, "*.pdf"))[:3]]
    conn = get_db()
    return jsonify({
        "PDF_FOLDER": PDF_FOLDER,
        "PDF_FOLDER_exists": os.path.isdir(PDF_FOLDER) if PDF_FOLDER else False,
        "sample_files": sample,
        "cwd": os.getcwd(),
        "index_docs": get_document_count(conn),
        "db_path": _DB_PATH,
    })


@app.route("/summary/<path:filename>")
def get_summary(filename):
    """Return extracted metadata summary for a document."""
    try:
        conn = get_db()
        row = conn.execute(
            "SELECT filename, text FROM documents WHERE relative_path = ? LIMIT 1",
            (filename,),
        ).fetchone()
        if not row:
            return jsonify({"error": "Document not found"}), 404

        text = row["text"]
        summary = {"filename": row["filename"]}
        company = extract_company(text)
        if company:
            summary["company"] = company
        invoice_date = extract_date(text)
        if invoice_date:
            summary["date"] = invoice_date
        total_amount = extract_total_amount(text)
        if total_amount:
            summary["amount"] = total_amount
        invoice_num = extract_invoice_number(text)
        if invoice_num:
            summary["invoice_number"] = invoice_num
        return jsonify(summary)
    except Exception as e:
        return jsonify({"error": str(e)}), 500




# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    def find_free(preferred):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("127.0.0.1", preferred))
            return s.getsockname()[1]
        except OSError:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]
        finally:
            s.close()

    try:
        candidate = int(os.getenv("PORT", 5000))
    except ValueError:
        candidate = 5000
    port = find_free(candidate)
    if port != candidate:
        print(f"Port {candidate} unavailable, using {port} instead.")
    try:
        app.run(host="127.0.0.1", port=port, debug=True)
    except OSError as e:
        print(str(e))
        print(f"Failed to start server on port {port}.")
