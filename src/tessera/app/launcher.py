"""Console-script entry: `tessera-app` -> `streamlit run` on the packaged app."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    from streamlit.web import cli as stcli

    app_path = str(Path(__file__).with_name("streamlit_app.py"))
    sys.argv = ["streamlit", "run", app_path, *sys.argv[1:]]
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
