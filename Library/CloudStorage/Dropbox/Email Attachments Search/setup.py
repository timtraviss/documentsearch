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
        # backend package itself, plus some dependencies that py2app
        # occasionally misses (especially those containing compiled
        # extensions).  charset_normalizer is indirectly required by
        # requests/httpx and the md__mypyc extension was not being bundled,
        # leading to "No module named 'charset_normalizer.md__mypyc'" errors
        # when reindexing.  Including the full package here forces it into
        # the app.
        'backend',
        'flask',
        'pdfminer',
        'dotenv',
        'jinja2',
        'charset_normalizer',
    ],
    'includes': [
        'backend.app',
        'backend.indexer',
        'backend.embeddings',
        # explicitly include the compiled extension too, just in case
        'charset_normalizer.md__mypyc',
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
