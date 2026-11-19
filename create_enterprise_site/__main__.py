"""Module entrypoint for `python -m create_enterprise_site`."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
