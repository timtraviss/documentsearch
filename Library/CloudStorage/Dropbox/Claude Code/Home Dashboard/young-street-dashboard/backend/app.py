import os
import json
import threading
from flask import Flask, send_from_directory, jsonify
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


@app.route('/')
def index():
    return send_from_directory(ROOT, 'index.html')


@app.route('/api/health')
def health():
    return jsonify({'status': 'ok'})


@app.route('/api/ask', methods=['POST'])
def api_ask():
    from flask import request
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


@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(ROOT, path)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
