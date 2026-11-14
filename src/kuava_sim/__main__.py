"""Start the live app: python -m kuava_sim (ARCHITECTURE_899eaea.md, Startup).

Start-up problems print one plain line and exit with code 1, never a
traceback (OQ-41).
"""

import sys


def _fail(message: str) -> int:
    print(f"Cannot start: {message}", file=sys.stderr)
    return 1


def main() -> int:
    try:
        import tkinter
    except ImportError:
        return _fail(
            "Tkinter is not installed. Install Python with Tcl/Tk support "
            "(on Linux the python3-tk package)."
        )
    try:
        root = tkinter.Tk()
    except tkinter.TclError:
        return _fail("no display available. Run the app from a desktop session.")
    try:
        from . import app

        app.App(root)
    except Exception as exc:  # any other start-up problem: one plain line
        try:
            root.destroy()
        except tkinter.TclError:
            pass
        return _fail(str(exc) or type(exc).__name__)
    root.wait_window(root)  # the Tk event loop, until this window is closed
    return 0


if __name__ == "__main__":
    sys.exit(main())
