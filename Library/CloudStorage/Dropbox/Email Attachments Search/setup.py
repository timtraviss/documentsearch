"""
Setup script for py2app to bundle Document Search as a macOS app.

Build the app with:
    python setup.py py2app

The resulting .app bundle will be in the dist/ folder.
"""
from setuptools import setup

# Build options for py2app
OPTIONS = {
    'argv_emulation': False,
    'packages': [
        'flask',
        'pdfminer',
        'dotenv',
        'jinja2',
    ],
    'includes': [
        'backend',
        'backend.app',
        'backend.indexer',
        'backend.embeddings',
    ],
    'resources': [
        'backend/templates',
        '.env.example',
    ],
    'excludes': [
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        'pytest',
        'pip',
        'setuptools',
        'wheel',
    ],
    'plist': {
        'LSBackgroundOnly': False,
        'NSPrincipalClass': 'NSApplication',
        'CFBundleIdentifier': 'com.personal.documentsearch',
        'CFBundleVersion': '0.1.0',
        'CFBundleShortVersionString': '0.1',
    },
}

setup(
    name='Document Search',
    version='0.1.0',
    description='Search and index PDF documents from your email attachments',
    author='Timothy Traviss',
    url='https://github.com/timtraviss/documentsearch',
    app=['app_launcher.py'],
    options={'py2app': OPTIONS},
)
