"""Pack installer — scaffolding for ``polarity install pack``.

Full implementation planned for a future release.  For now this prints
a helpful roadmap and instructs the user to install packs manually.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _user_packs_dir() -> Path:
    env = os.environ.get("POLARITY_PACKS_DIR")
    if env:
        return Path(env)
    return Path.home() / ".polarity" / "packs"


def install_pack(source: str) -> None:
    """Install a persona pack from a git URL or package name.

    Parameters
    ----------
    source:
        A git clone URL (``https://…``, ``git@…``) or a pip-installable
        package name.
    """
    target = _user_packs_dir()
    print(f"📦 Installing pack from: {source}")
    print(f"   Target directory: {target}")
    print()
    print("🚧 Automated pack installation is not yet implemented.")
    print()
    print("   Planned workflow:")
    print("   1. Clone / download the pack source")
    print("   2. Validate config.json + system_prompt.txt exist")
    print("   3. Copy to the target directory above")
    print()
    print("   Manual install:")
    print(f"     mkdir -p {target}")
    print(f"     git clone {source} {target}/<pack_name>")
    sys.exit(0)
