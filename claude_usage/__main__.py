"""
__main__.py

Entry point: `python -m claude_usage` (loop) or `python -m claude_usage --once`.
"""

import argparse
import logging
import sys
import time

from .collector import run_collection
from .config import ConfigError, load_settings
from .logger import setup_logger


def main() -> int:
    """Parse arguments and run the collector.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description="Collecte l'utilisation de Claude.")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Une seule collecte puis arrêt (test).",
    )
    parser.add_argument("--debug", action="store_true", help="Journalisation détaillée.")
    args = parser.parse_args()

    setup_logger(logging.DEBUG if args.debug else logging.INFO)

    if args.once:
        result = run_collection()
        if not result.ok:
            sys.stderr.write(result.message + "\n")
        return 0 if result.ok else 1

    try:
        interval = load_settings().poll_interval_seconds
    except ConfigError as exc:
        logging.error("Configuration error: %s", exc)
        sys.stderr.write(f"Erreur de configuration : {exc}. Vérifiez le fichier .env.\n")
        return 2

    logging.info("Collector started, interval=%ds", interval)
    try:
        while True:
            run_collection()
            time.sleep(interval)
    except KeyboardInterrupt:
        logging.info("Collector stopped by user")
    return 0


if __name__ == "__main__":
    sys.exit(main())
