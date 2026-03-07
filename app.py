"""Standalone launcher for the Polarity Agent Streamlit UI.

Run directly::

    streamlit run app.py

Or via the CLI::

    polarity serve --port 8501
"""

import subprocess
import sys
from pathlib import Path


def main() -> None:
    web_module = Path(__file__).resolve().parent / "src" / "polarity_agent" / "web.py"
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(web_module), "--server.port=8501"],
        check=True,
    )


if __name__ == "__main__":
    main()
