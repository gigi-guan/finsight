"""Run on Vercel after dependencies install. Applies migrations when a hosted DB is configured."""

from __future__ import annotations

import os
import subprocess
import sys


def main() -> None:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url or "localhost" in url or "127.0.0.1" in url:
        print("No hosted DATABASE_URL; skipping alembic upgrade.")
        return
    print("Applying database migrations...")
    subprocess.check_call([sys.executable, "-m", "alembic", "upgrade", "head"])


if __name__ == "__main__":
    main()
