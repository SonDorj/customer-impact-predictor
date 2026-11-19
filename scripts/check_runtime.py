"""Verify the Python version used for the bundled model."""

import sys

if sys.version_info[:2] != (3, 14):
    raise SystemExit(
        "Use Python 3.14 for the supplied locked model environment. "
        "No environment files were changed."
    )
print("Python 3.14 is available.")
