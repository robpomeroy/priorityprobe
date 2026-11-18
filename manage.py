#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import ctypes
import os
import sys

for _candidate in (
    "/usr/local/aws-cli/v2/2.27.11/dist/libsqlite3.so.0",
    "/usr/local/aws-cli/v2/current/dist/libsqlite3.so.0",
):
    if os.path.exists(_candidate):
        try:
            ctypes.CDLL(_candidate, mode=ctypes.RTLD_GLOBAL)
            break
        except OSError:
            pass


def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
