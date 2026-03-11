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
    'iconfile': 'app_icon.icns',
    'packages': [
        # backend package itself, plus some dependencies that py2app
        # occasionally misses (especially those containing compiled
        # extensions).  charset_normalizer is indirectly required by
        # requests/httpx and the md__mypyc extension was not being bundled,
        # leading to "No module named 'charset_normalizer.md__mypyc'" errors
        # when reindexing.  Including the full package here forces it into
        # the app.  Similarly, cffi is required by cryptography (which is used
        # for security operations), and its compiled _cffi_backend module must
        # be explicitly included to avoid "No module named '_cffi_backend'" errors.
        'backend',
        'flask',
        'pdfminer',
        'dotenv',
        'jinja2',
        'charset_normalizer',
        'cffi',
        'webview',
    ],
    'includes': [
        'backend.app',
        'backend.indexer',
        'backend.database',
        'backend.embeddings',
        # explicitly include compiled extensions
        'charset_normalizer.md__mypyc',
        '_cffi_backend',
        '_sqlite3',
    ],
    'resources': [
        'backend/templates',
        'backend/static',
        '.env',
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
        'CFBundleVersion': '0.2.0',
        'CFBundleShortVersionString': '0.2',
        'NSDesktopFolderUsageDescription': 'Document Search needs access to read PDF files from your folders.',
        'NSDocumentsFolderUsageDescription': 'Document Search needs access to read PDF files from your folders.',
        'NSDownloadsFolderUsageDescription': 'Document Search needs access to read PDF files from your folders.',
    },
}

setup(
    name='Document Search',
    version='0.2.0',
    description='Search and index PDF documents from your email attachments',
    author='Timothy Traviss',
    url='https://github.com/timtraviss/documentsearch',
    app=['app_launcher.py'],
    options={'py2app': OPTIONS},
)
