"""Standalone launcher for the Polarity Agent Web UI (FastAPI + Vanilla HTML/JS).

Run directly::

    python app.py

Or via the CLI::

    polarity serve --port 7860
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))


def main() -> None:
    from polarity_agent.server import main as server_main

    server_main(host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()
