import os
import json
from urllib.parse import unquote
from flask import Flask, render_template, request, send_from_directory, jsonify
from dotenv import load_dotenv

# load .env
load_dotenv()

PDF_FOLDER = os.getenv("PDF_FOLDER")
INDEX_FILE = os.path.join(os.path.dirname(__file__), "index.json")

app = Flask(__name__)

# load index into memory
if os.path.exists(INDEX_FILE):
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        documents = json.load(f)
else:
    documents = []

# Try to load embeddings module for semantic search
try:
    from embeddings import search as semantic_search
    HAS_EMBEDDINGS = os.path.exists(os.path.join(os.path.dirname(__file__), "vector.faiss"))
except ImportError:
    HAS_EMBEDDINGS = False

# Optional secret token to protect the reindex endpoint for non-local deployments
REINDEX_TOKEN = os.getenv("REINDEX_TOKEN")

# simple versioning for display in the UI
APP_VERSION = "0.1"

# Tags storage (user-applied metadata: type, status, company, year)
TAGS_FILE = os.path.join(os.path.dirname(__file__), "tags.json")

def load_tags():
    try:
        if os.path.exists(TAGS_FILE):
            with open(TAGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

# Status/logs for a running reindex job (simple in-memory structure)
reindex_status = {
    "running": False,
    "logs": [],
    "count": 0,
    "error": None,
}

import re

@app.route("/")
def home():
    return render_template(
        "search.html",
        has_embeddings=HAS_EMBEDDINGS,
        reindex_token_present=bool(REINDEX_TOKEN),
        version=APP_VERSION
    )

@app.route("/search")
def search():
    q = request.args.get("q", "").lower()
    search_type = request.args.get("type", "semantic" if HAS_EMBEDDINGS else "text")

    # Existing text filters
    filter_company = request.args.get("company", "").lower()
    filter_date = request.args.get("date", "")
    filter_amount = request.args.get("amount", "")
    filter_mode = request.args.get("mode", "and").lower()

    # Tag filters (applied post-search)
    tag_type = request.args.get("tag_type", "").lower()
    tag_year = request.args.get("tag_year", "")

    has_query = bool(q or filter_company or filter_date or filter_amount)
    has_tag_filters = bool(tag_type or tag_year)

    if not has_query and not has_tag_filters:
        return jsonify([])

    tags_data = load_tags()
    # O(1) doc lookup by relative_path
    doc_index = {doc.get("relative_path", ""): doc for doc in documents}

    results = []

    # Tag-only browse: no text query, iterate tags directly
    if not has_query and has_tag_filters:
        for rel_path, tag in tags_data.items():
            if tag_type and tag.get("type", "").lower() != tag_type:
                continue
            if tag_year and tag.get("year", "") != tag_year:
                continue
            doc = doc_index.get(rel_path)
            if not doc:
                continue
            text = doc.get("text", "")
            fname = doc.get("filename", "")
            results.append({
                "filename": fname,
                "path": rel_path,
                "snippet": text[:300],
                "company": (tag.get("company")
                            or extract_company(text)
                            or extract_company_from_filename(fname)
                            or ""),
                "date": tag.get("year") or extract_date(text) or "",
                "amount": extract_total_amount(text) or "",
                "tags": tag,
            })
        return jsonify(results[:20])

    # Normal search (with or without tag filters)
    if search_type == "semantic" and HAS_EMBEDDINGS:
        try:
            top_k = 50 if has_tag_filters else 10
            search_results = semantic_search(q, top_k=top_k)
            # Enrich semantic results with extracted metadata
            for r in search_results:
                doc = doc_index.get(r.get("path", ""), {})
                text = doc.get("text", "") if doc else ""
                r["company"] = extract_company(text) or ""
                r["date"] = extract_date(text) or ""
                r["amount"] = extract_total_amount(text) or ""
            results = search_results
        except Exception as e:
            print(f"Semantic search error: {e}")
            results = text_search(q, filter_company, filter_date, filter_amount, filter_mode)
    else:
        results = text_search(q, filter_company, filter_date, filter_amount, filter_mode)

    # Enrich results with tag data
    for r in results:
        r["tags"] = tags_data.get(r.get("path", ""), {})

    # Apply tag filters if set
    if has_tag_filters:
        filtered = []
        for r in results:
            t = r.get("tags", {})
            if tag_type and t.get("type", "").lower() != tag_type:
                continue
            if tag_year and t.get("year", "") != tag_year:
                continue
            filtered.append(r)
        results = filtered

    return jsonify(results[:20])


@app.route("/reindex", methods=["POST"])
def reindex():
    """Regenerate the PDF index and refresh the in-memory documents list.

    This endpoint is intentionally a POST and is intended for local/dev use.
    """
    # Authenticate with token if configured
    if REINDEX_TOKEN:
        provided = request.headers.get('X-Reindex-Token') or request.json and request.json.get('token')
        if not provided or provided != REINDEX_TOKEN:
            return jsonify({"status": "error", "error": "invalid or missing token"}), 403

    # Prevent concurrent reindex jobs
    if reindex_status["running"]:
        return jsonify({"status": "error", "error": "reindex already running"}), 409

    # Start background worker so UI can poll status
    import threading

    def _log(msg):
        reindex_status["logs"].append(msg)

    def worker():
        try:
            reindex_status["running"] = True
            reindex_status["logs"] = []
            reindex_status["count"] = 0
            reindex_status["error"] = None

            _log("Starting reindex...")

            # use package-qualified import to work regardless of cwd
            from backend.indexer import scan_pdfs, save_index

            folder = PDF_FOLDER or os.getenv("PDF_FOLDER")
            if not folder or not os.path.isdir(folder):
                reindex_status["error"] = "PDF_FOLDER not configured or not found"
                _log(reindex_status["error"])
                return

            _log(f"Scanning folder: {folder}")

            def progress_cb(path, idx, total):
                _log(f"Indexed ({idx}/{total}): {path.split('/')[-1]}")

            docs = scan_pdfs(folder, progress_callback=progress_cb)
            _log(f"Saving index ({len(docs)} documents)")
            save_index(docs)

            # update in-memory documents
            global documents
            documents = docs

            reindex_status["count"] = len(docs)
            _log("Reindex complete")
        except Exception as e:
            reindex_status["error"] = str(e)
            _log(f"Error: {e}")
        finally:
            reindex_status["running"] = False

    t = threading.Thread(target=worker, daemon=True)
    t.start()

    return jsonify({"status": "ok", "message": "reindex started"})


@app.route('/reindex/status')
def reindex_status_api():
    # Return current status and last N logs
    logs = reindex_status.get('logs', [])[-200:]
    return jsonify({
        'running': reindex_status.get('running', False),
        'logs': logs,
        'count': reindex_status.get('count', 0),
        'error': reindex_status.get('error')
    })

@app.route("/tags/<path:filename>", methods=["GET"])
def get_doc_tags(filename):
    """Return saved tags for a document, auto-populated from extraction if not yet set."""
    tags_data = load_tags()
    tag = tags_data.get(filename, {})
    if not tag:
        for doc in documents:
            if doc.get("relative_path") == filename or doc.get("path", "").endswith(filename):
                text = doc.get("text", "")
                fname = doc.get("filename", "")
                date = extract_date(text) or ""
                year = date[:4] if date else ""
                company = (extract_company(text)
                           or extract_company_from_filename(fname)
                           or "")
                tag = {
                    "type": "",
                    "company": company,
                    "year": year,
                    "auto": True,
                }
                break
    return jsonify(tag)


@app.route("/tags/<path:filename>", methods=["POST"])
def save_doc_tags(filename):
    """Save user-applied tags for a document."""
    data = request.get_json(force=True) or {}
    tags_data = load_tags()
    tags_data[filename] = {
        "type": data.get("type", ""),
        "company": data.get("company", ""),
        "year": str(data.get("year", "")),
    }
    with open(TAGS_FILE, "w", encoding="utf-8") as f:
        json.dump(tags_data, f, indent=2)
    return jsonify({"status": "ok"})


def text_search(q, filter_company="", filter_date="", filter_amount="", filter_mode="and"):
    """Search by keyword and optional filters.

    filter_mode may be "and" (all filters must match) or "or" (any filter).
    """
    _STOP_WORDS = {'a', 'an', 'the', 'at', 'in', 'on', 'of', 'for', 'to', 'and', 'or', 'is', 'was', 'are', 'with', 'by', 'from'}
    results = []
    tokens = [t for t in q.lower().split() if t not in _STOP_WORDS] if q else []

    for doc in documents:
        # Check keyword match — all meaningful tokens must appear in text or filename
        doc_text = (doc.get("text", "") + " " + doc.get("filename", "")).lower()
        text_match = (not tokens) or all(t in doc_text for t in tokens)
        if not text_match:
            continue
        
        # Extract metadata for filtering
        text_content = doc.get("text", "")
        company = extract_company(text_content) or ""
        date = extract_date(text_content) or ""
        amount = extract_total_amount(text_content) or ""
        
        # Compute individual filter booleans
        pass_company = True
        pass_date = True
        pass_amount = True

        if filter_company:
            pass_company = filter_company in company.lower()

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
                pass_amount = (min_amt <= amount_num <= max_amt)
            except ValueError:
                pass_amount = True

        if filter_mode == "or":
            if not (pass_company or pass_date or pass_amount):
                continue
        else:  # and
            if not (pass_company and pass_date and pass_amount):
                continue

        results.append({
            "filename": doc["filename"],
            "path": doc.get("relative_path", doc["path"]),
            "snippet": doc.get("text", "")[:300],
            "company": company,
            "date": date,
            "amount": amount
        })
    
    return results[:20]

@app.route("/pdf/<path:filename>")
def serve_pdf(filename):
    """Serve PDF files from the configured PDF folder (inline, not download)."""
    try:
        filename = unquote(filename)
        return send_from_directory(PDF_FOLDER, filename, as_attachment=False)
    except Exception as e:
        return jsonify({"error": f"File not found: {e}"}), 404

@app.route("/summary/<path:filename>")
def get_summary(filename):
    """Generate and return a focused summary of a PDF file."""
    try:
        # Find the document in our index
        doc = None
        for d in documents:
            if d.get("relative_path") == filename or d.get("path").endswith(filename):
                doc = d
                break
        
        if not doc:
            return jsonify({"error": "Document not found"}), 404
        
        text = doc.get("text", "")
        
        summary = {
            "filename": doc.get("filename", "")
        }
        
        # Extract company/vendor name
        company = extract_company(text)
        if company:
            summary["company"] = company
        
        # Extract invoice date
        invoice_date = extract_date(text)
        if invoice_date:
            summary["date"] = invoice_date
        
        # Extract invoice amount
        total_amount = extract_total_amount(text)
        if total_amount:
            summary["amount"] = total_amount
        
        # Invoice number
        invoice_num = extract_invoice_number(text)
        if invoice_num:
            summary["invoice_number"] = invoice_num
        
        return jsonify(summary)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def extract_company_from_filename(filename):
    """Try to infer a company name from the PDF filename.

    Many filenames look like 'Spark Invoice 2024.pdf' or 'spark_nz_receipt_01.pdf'.
    We strip the extension, replace separators, remove common noise words and
    return the first meaningful words as a candidate company name.
    """
    import re
    name = os.path.splitext(filename)[0]
    name = re.sub(r'[_\-]+', ' ', name)
    # Remove common document-type and date noise
    noise = (r'\b(invoice|receipt|statement|quote|contract|tax|gst|nz|pdf|'
             r'final|draft|copy|order|ref|no|number|'
             r'\d{4}|\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)\b')
    cleaned = re.sub(noise, '', name, flags=re.IGNORECASE).strip()
    words = [w for w in cleaned.split() if len(w) > 1]
    if words:
        return ' '.join(words[:3])
    return None


def extract_company(text):
    """Extract company/vendor name from text."""
    lines = text.split('\n')
    
    # Look for common company keywords
    company_keywords = ['from:', 'vendor:', 'billed by:', 'company:', 'invoice from:']
    
    for i, line in enumerate(lines[:30]):  # Check first 30 lines
        line_lower = line.lower()
        for keyword in company_keywords:
            if keyword in line_lower:
                # Get the part after the keyword
                parts = line.split(':')
                if len(parts) > 1:
                    company = parts[-1].strip()
                    if company and len(company) > 2:
                        return company[:100]
    
    # If no keyword found, look for first capitalized line that looks like a company
    for line in lines[:20]:
        line = line.strip()
        if line and len(line) > 5 and len(line) < 80:
            # Check if it looks like a company name (mostly caps or Title Case)
            if any(c.isupper() for c in line) and not any(c.isdigit() for c in line[:5]):
                return line
    
    return None

def extract_date(text):
    """Extract invoice date from text."""
    import re
    
    # Look for date patterns near "date:" or "invoice date:" first
    keywords = ['date:', 'date ', 'dated ', 'invoice date:']
    lines = text.split('\n')
    
    for line in lines[:30]:
        line_lower = line.lower()
        for keyword in keywords:
            if keyword in line_lower:
                # Extract date from this line
                dates = re.findall(
                    r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})',
                    line
                )
                if dates:
                    return dates[0]
    
    # Fallback: find any date in the text
    all_dates = re.findall(
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})',
        text[:500]
    )
    if all_dates:
        return all_dates[0]
    
    return None

def extract_total_amount(text):
    """Extract the total/invoice amount from text."""
    import re
    
    # Look for "total" or "amount due" patterns with amounts
    keywords = ['total:', 'amount due:', 'total amount:', 'invoice total:', 'balance due:']
    lines = text.split('\n')
    
    for line in lines:
        line_lower = line.lower()
        for keyword in keywords:
            if keyword in line_lower:
                # Extract amount from this line
                amounts = re.findall(
                    r'\$[\d,]+\.?\d{0,2}|NZ\$[\d,]+\.?\d{0,2}|[\d,]+\.\d{2}(?:\s*NZD?)?',
                    line
                )
                if amounts:
                    return amounts[-1]  # Take the last amount found (usually the total)
    
    # Fallback: find the largest amount in the document
    all_amounts = re.findall(
        r'\$[\d,]+\.?\d{0,2}|NZ\$[\d,]+\.?\d{0,2}',
        text
    )
    if all_amounts:
        # Try to parse and return the largest
        try:
            def parse_amount(s):
                return float(re.sub(r'[^\d.]', '', s))
            largest = max(all_amounts, key=parse_amount)
            return largest
        except:
            return all_amounts[-1]
    
    return None

def extract_invoice_number(text):
    """Extract invoice/reference number from text."""
    import re
    
    keywords = ['invoice #:', 'invoice no:', 'invoice number:', 'ref:', 'reference:', 'inv#:']
    lines = text.split('\n')
    
    for line in lines[:40]:
        line_lower = line.lower()
        for keyword in keywords:
            if keyword in line_lower:
                # Extract the number
                parts = line.split(':')
                if len(parts) > 1:
                    num = parts[-1].strip().split()[0]  # Get first token
                    if num and len(num) < 30 and (any(c.isdigit() for c in num)):
                        return num
    
    return None

if __name__ == "__main__":
    # allow port override via environment variable (useful when 5000 is occupied)
    import socket

    def find_free(preferred):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(('127.0.0.1', preferred))
            return s.getsockname()[1]
        except OSError:
            s.bind(('127.0.0.1', 0))
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
        print(f"Failed to start server on port {port}. You may need to choose a different PORT or stop the process using it.")
