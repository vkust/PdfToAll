"""Frozen-binary entry point (PyInstaller).

Kept separate from the console script so the packaged executable has one
predictable call: `pdftoall <subcommand> ...`.
"""

import sys

from pdftoall.cli import main

if __name__ == "__main__":
    sys.exit(main())
