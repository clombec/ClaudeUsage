"""
manage.py

Django command-line utility for the usage dashboard.
"""

import os
import sys


def main() -> None:
    """Run Django administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "usage_site.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
