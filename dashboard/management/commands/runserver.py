"""
runserver.py

Overrides `manage.py runserver` to listen on port 8060 by default,
while keeping static file serving from django.contrib.staticfiles.
"""

from django.contrib.staticfiles.management.commands.runserver import (
    Command as StaticfilesRunserverCommand,
)

DEFAULT_PORT = "8060"


class Command(StaticfilesRunserverCommand):
    """runserver with DEFAULT_PORT as the default port."""

    default_port = DEFAULT_PORT
