import ssl
import os
import sys

# Fix SSL certificates in PyInstaller bundle
if getattr(sys, 'frozen', False):
    # Try to use certifi's certificates
    try:
        import certifi
        os.environ['SSL_CERT_FILE'] = certifi.where()
        os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
        ssl._create_default_https_context = ssl.create_default_context
    except ImportError:
        # Fallback: disable SSL verification for model downloads only
        ssl._create_default_https_context = ssl._create_unverified_context
