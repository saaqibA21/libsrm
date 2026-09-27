"""
WSGI entry point for Cloud Deployment (Render, Railway, PythonAnywhere, Heroku)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from webapp.app import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
