import os
import sys
from flask import Flask, send_from_directory, jsonify
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
app = Flask(__name__)


@app.route('/')
def index():
    return send_from_directory(ROOT, 'index.html')


@app.route('/api/health')
def health():
    return jsonify({'status': 'ok'})


@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(ROOT, path)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
