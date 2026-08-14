"""Single place that loads environment configuration.

Every module needing an API key imports this rather than calling load_dotenv
itself. Before this existed, `retrieve.py` read COHERE_API_KEY straight from
os.environ and only worked because importing `answer.py` first happened to call
load_dotenv as a side effect — so the API ran fine while standalone scripts like
`build_index.py` died with a bare KeyError.

Import it for the side effect, or call `require()` for a readable failure:

    from core.env import require
    api_key = require("COHERE_API_KEY")
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# backend/.env is the real one; the repo-root .env is a partial leftover.
# Both are loaded, nearest first, and load_dotenv does not overwrite values
# already set — so a real environment variable always wins over a file.
_BACKEND_DIR = Path(__file__).resolve().parents[1]
_SEARCH_PATHS = (_BACKEND_DIR / ".env", _BACKEND_DIR.parent / ".env")

for _path in _SEARCH_PATHS:
    if _path.exists():
        load_dotenv(dotenv_path=_path, override=False)


def require(name: str) -> str:
    """Fetch a required variable, or fail with something actionable."""
    value = os.getenv(name)
    if not value:
        searched = "\n".join(f"  - {p}" for p in _SEARCH_PATHS)
        raise RuntimeError(
            f"Missing required environment variable: {name}\n"
            f"Looked for a .env file at:\n{searched}\n"
            f"Set it in backend/.env or export it before running."
        )
    return value
