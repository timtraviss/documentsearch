import os
import json
import threading
from flask import Flask, send_from_directory, jsonify, request
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
app = Flask(__name__)

_anthropic = None

def _ant():
    global _anthropic
    if _anthropic is None:
        _anthropic = Anthropic()
    return _anthropic

PROPERTY_JSON = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'property.json')
)

_index_state = {
    'running':      False,
    'progress':     '',
    'log':          [],
    'error':        None,
}
_log_lock = threading.Lock()


def _run_index(folder):
    _index_state['running'] = True
    with _log_lock:
        _index_state['log'] = []
    _index_state['error'] = None

    def log(msg):
        with _log_lock:
            _index_state['log'].append(msg)
        _index_state['progress'] = msg

    try:
        from database import init_db, get_all_documents_with_text
        from indexer import scan_pdfs
        from embeddings import build_embeddings

        init_db()
        log('Scanning PDFs...')
        indexed, skipped = scan_pdfs(folder, progress_callback=log)
        log(f'Indexed {indexed} new, skipped {skipped} unchanged')

        log('Building embeddings...')
        docs = get_all_documents_with_text()
        build_embeddings(docs, progress_callback=log)
        log('Complete')
        _index_state['error'] = None
    except Exception as exc:
        _index_state['error'] = str(exc)
        log(f'ERROR: {exc}')
    finally:
        _index_state['running'] = False


@app.route('/')
def index():
    return send_from_directory(ROOT, 'index.html')


@app.route('/api/health')
def health():
    return jsonify({'status': 'ok'})


@app.route('/api/ask', methods=['POST'])
def api_ask():
    body = request.get_json(force=True) or {}
    query = (body.get('query') or '').strip()
    messages = body.get('messages') or []

    if not query:
        return jsonify({'error': 'query required'}), 400

    # Load property facts as system context
    try:
        with open(PROPERTY_JSON) as f:
            property_ctx = json.dumps(json.load(f), indent=2)
    except Exception:
        property_ctx = '{}'

    # Vector search (graceful fallback if index not built)
    try:
        from embeddings import search_chunks
        chunks = search_chunks(query, top_k=6)
    except Exception:
        chunks = []

    doc_ctx = ''.join(
        f'\n\n---\nDocument: {c["name"]} ({c["filename"]})\n{c["snippet"]}'
        for c in chunks
    )

    system_prompt = (
        'You are the House Brain for 11 Young Street, Scotts Landing, '
        'Mahurangi East, New Zealand.\n'
        'Answer questions about the property using the facts and document excerpts provided. '
        'Be concise. Cite the document name when you draw from it.\n\n'
        f'PROPERTY FACTS:\n{property_ctx}\n\n'
        f'RELEVANT DOCUMENT EXCERPTS:{doc_ctx or " (none — index not yet built)"}'
    )

    history = [m for m in messages if m.get('role') in ('user', 'assistant')]
    history.append({'role': 'user', 'content': query})

    resp = _ant().messages.create(
        model='claude-sonnet-4-6',
        max_tokens=1024,
        system=system_prompt,
        messages=history,
    )
    answer = resp.content[0].text

    seen = set()
    sources = []
    for c in chunks:
        if c['filename'] not in seen:
            seen.add(c['filename'])
            sources.append({
                'filename': c['filename'],
                'name':     c['name'],
                'snippet':  c['snippet'],
            })

    return jsonify({'answer': answer, 'sources': sources})


@app.route('/api/index', methods=['POST'])
def api_index():
    if _index_state['running']:
        return jsonify({'status': 'already_running'}), 409

    folder = os.environ.get('DOCUMENTS_FOLDER', '').strip()
    if not folder or not os.path.isdir(folder):
        return jsonify({'error': 'DOCUMENTS_FOLDER not set or not a valid directory'}), 500

    thread = threading.Thread(target=_run_index, args=(folder,), daemon=True)
    thread.start()
    return jsonify({'status': 'started'})


@app.route('/api/index/status')
def api_index_status():
    from database import get_document_count, get_last_indexed
    try:
        doc_count    = get_document_count()
        last_indexed = get_last_indexed()
    except Exception:
        doc_count    = 0
        last_indexed = None

    with _log_lock:
        log_copy = list(_index_state['log'][-5:])

    return jsonify({
        'running':      _index_state['running'],
        'progress':     _index_state['progress'],
        'log':          log_copy,
        'error':        _index_state['error'],
        'doc_count':    doc_count,
        'last_indexed': last_indexed,
    })


@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(ROOT, path)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
