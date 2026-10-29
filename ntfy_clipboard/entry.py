"""Single executable entry point: GUI by default, service with --service."""

from __future__ import annotations

import sys


def main() -> int:
    if "--service" in sys.argv:
        from ntfy_clipboard.__main__ import main as cli_main

        return cli_main(sys.argv[1:])

    from ntfy_clipboard.gui import main as gui_main

    return gui_main(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
