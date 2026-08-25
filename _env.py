"""Load .env for local runs. In CI the secrets are already in the environment."""
import io, os
from pathlib import Path


def load() -> None:
    p = Path(__file__).resolve().parent / ".env"
    if not p.exists():
        return
    for line in io.open(p, encoding="utf-8"):
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())
