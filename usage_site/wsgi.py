"""
wsgi.py

WSGI entry point for the usage dashboard project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "usage_site.settings")
application = get_wsgi_application()
