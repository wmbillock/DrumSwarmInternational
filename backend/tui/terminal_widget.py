"""Cross-platform terminal emulator widget for Textual.

Uses pyte for VT100 screen emulation and platform-specific PTY backends:
- Windows: winpty (ConPTY)
- Unix: pty module

Renders the terminal screen as Rich Text inside a Textual widget.
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Any

import pyte
from rich.segment import Segment
from rich.style import Style
from textual import work
from textual.events import Resize
from textual.strip import Strip
from textual.widget import Widget

# ── pyte color → Rich color mapping ─────────────────────────────────

_PYTE_COLORS = {
    "black": "black",
    "red": "red",
    "green": "green",
    "brown": "yellow",
    "blue": "blue",
    "magenta": "magenta",
    "cyan": "cyan",
    "white": "white",
    "default": "default",
    # Bright variants
    "brightblack": "bright_black",
    "brightred": "bright_red",
    "brightgreen": "bright_green",
    "brightbrown": "bright_yellow",
    "brightblue": "bright_blue",
    "brightmagenta": "bright_magenta",
    "brightcyan": "bright_cyan",
    "brightwhite": "bright_white",
}


def _pyte_color(color: str, role: str = "color") -> str | None:
    """Convert a pyte color name to a Rich color string."""
    if not color or color == "default":
        return None
    # Named color
    mapped = _PYTE_COLORS.get(color)
    if mapped and mapped != "default":
        return mapped
    # 256-color or hex (pyte stores these as strings)
    if len(color) == 6:
        try:
            int(color, 16)
            return f"#{color}"
        except ValueError:
            pass
    return None


def _char_style(char: pyte.screens.Char) -> Style:
    """Convert a pyte Char's attributes to a Rich Style."""
    fg = _pyte_color(char.fg)
    bg = _pyte_color(char.bg)
    return Style(
        color=fg,
        bgcolor=bg,
        bold=char.bold,
        italic=char.italics,
        underline=char.underscore,
        strike=char.strikethrough,
        reverse=char.reverse,
    )


# ── PTY abstraction ─────────────────────────────────────────────────

class _PtyBackend:
    """Abstract PTY backend."""

    def spawn(self, command: str, cols: int, rows: int, cwd: str | None = None) -> None:
        raise NotImplementedError

    def read(self) -> str:
        raise NotImplementedError

    def write(self, data: str) -> None:
        raise NotImplementedError

    def set_size(self, cols: int, rows: int) -> None:
        raise NotImplementedError

    def is_alive(self) -> bool:
        raise NotImplementedError

    def terminate(self) -> None:
        raise NotImplementedError


class _WinPtyBackend(_PtyBackend):
    """Windows PTY using pywinpty."""

    def __init__(self) -> None:
        self._pty: Any = None
        self._spawn_error: str | None = None

    def spawn(self, command: str, cols: int, rows: int, cwd: str | None = None) -> None:
        from winpty import PTY
        self._pty = PTY(cols, rows)
        self._pty.spawn(command, cwd=cwd)

    def read(self) -> str:
        if self._pty is None:
            return ""
        try:
            data = self._pty.read(blocking=False)
            return data if data else ""
        except Exception:
            return ""

    def write(self, data: str) -> None:
        if self._pty:
            self._pty.write(data)

    def set_size(self, cols: int, rows: int) -> None:
        if self._pty:
            try:
                self._pty.set_size(cols, rows)
            except Exception:
                pass

    def is_alive(self) -> bool:
        if self._pty is None:
            return False
        try:
            return self._pty.isalive()
        except Exception:
            return False

    def terminate(self) -> None:
        pty = self._pty
        self._pty = None
        if pty is not None:
            # Kill the spawned process so any blocking reads unblock
            try:
                pid = pty.pid
                if pid:
                    import subprocess
                    subprocess.run(
                        ["taskkill", "/F", "/PID", str(pid)],
                        capture_output=True, timeout=3,
                    )
            except Exception:
                pass


class _UnixPtyBackend(_PtyBackend):
    """Unix PTY using pty + os modules."""

    def __init__(self) -> None:
        self._fd: int | None = None
        self._pid: int | None = None

    def spawn(self, command: str, cols: int, rows: int, cwd: str | None = None) -> None:
        import pty
        import shlex
        args = shlex.split(command)
        self._pid, self._fd = pty.fork()
        if self._pid == 0:
            # Child process — set working directory before exec
            if cwd:
                os.chdir(cwd)
            os.execvp(args[0], args)
        else:
            self.set_size(cols, rows)
            # Set non-blocking
            import fcntl
            flags = fcntl.fcntl(self._fd, fcntl.F_GETFL)
            fcntl.fcntl(self._fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

    def read(self) -> str:
        if self._fd is None:
            return ""
        try:
            data = os.read(self._fd, 65536)
            return data.decode("utf-8", errors="replace") if data else ""
        except (OSError, BlockingIOError):
            return ""

    def write(self, data: str) -> None:
        if self._fd is not None:
            os.write(self._fd, data.encode("utf-8"))

    def set_size(self, cols: int, rows: int) -> None:
        if self._fd is not None:
            import fcntl
            import struct
            import termios
            winsize = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(self._fd, termios.TIOCSWINSZ, winsize)

    def is_alive(self) -> bool:
        if self._pid is None:
            return False
        try:
            pid, _ = os.waitpid(self._pid, os.WNOHANG)
            return pid == 0
        except ChildProcessError:
            return False

    def terminate(self) -> None:
        import signal
        if self._pid:
            try:
                os.kill(self._pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        if self._fd is not None:
            try:
                os.close(self._fd)
            except OSError:
                pass
        self._fd = None
        self._pid = None


def _create_backend() -> _PtyBackend:
    if sys.platform == "win32":
        return _WinPtyBackend()
    else:
        return _UnixPtyBackend()


# ── Key mapping ──────────────────────────────────────────────────────

_KEY_MAP = {
    "enter": "\r",
    "return": "\r",
    "tab": "\t",
    "backspace": "\x7f",
    "delete": "\x1b[3~",
    "escape": "\x1b",
    "up": "\x1b[A",
    "down": "\x1b[B",
    "right": "\x1b[C",
    "left": "\x1b[D",
    "home": "\x1b[H",
    "end": "\x1b[F",
    "pageup": "\x1b[5~",
    "pagedown": "\x1b[6~",
    "insert": "\x1b[2~",
    "f1": "\x1bOP",
    "f2": "\x1bOQ",
    "f3": "\x1bOR",
    "f4": "\x1bOS",
    "f5": "\x1b[15~",
    "f6": "\x1b[17~",
    "f7": "\x1b[18~",
    "f8": "\x1b[19~",
    "f9": "\x1b[20~",
    "f10": "\x1b[21~",
    "f11": "\x1b[23~",
    "f12": "\x1b[24~",
}


# ── Terminal Widget ──────────────────────────────────────────────────

class TerminalWidget(Widget, can_focus=True):
    """A terminal emulator widget that runs a command in a PTY."""

    DEFAULT_CSS = """
    TerminalWidget {
        background: #1a1a2e;
        color: #e0e0e0;
    }
    """

    def __init__(
        self,
        command: str | None = None,
        *,
        cwd: str | None = None,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        if command is None:
            command = "cmd.exe" if sys.platform == "win32" else os.environ.get("SHELL", "/bin/bash")
        self._command = command
        self._cwd = cwd
        self._backend: _PtyBackend | None = None
        self._screen: pyte.Screen | None = None
        self._stream: pyte.Stream | None = None
        self._pty_active = False
        self._cols = 80
        self._rows = 24
        self._spawn_error: str | None = None

    def on_mount(self) -> None:
        self._cols = self.size.width
        self._rows = self.size.height
        if self._cols < 1:
            self._cols = 80
        if self._rows < 1:
            self._rows = 24
        self.start()

    def start(self) -> None:
        """Start the PTY and begin reading."""
        if self._pty_active:
            return
        self._screen = pyte.Screen(self._cols, self._rows)
        self._stream = pyte.Stream(self._screen)
        self._backend = _create_backend()
        try:
            self._backend.spawn(self._command, self._cols, self._rows, cwd=self._cwd)
        except Exception as e:
            self._spawn_error = f"Failed to start terminal: {e}"
            self._backend = None
            return
        self._pty_active = True
        self._poll_pty()

    def stop(self) -> None:
        """Stop reading and terminate the PTY."""
        self._pty_active = False
        if self._backend:
            self._backend.terminate()
            self._backend = None

    @work(thread=True)
    def _poll_pty(self) -> None:
        """Poll the PTY for output in a background thread."""
        import time
        # Give the shell a moment to start up
        time.sleep(0.5)
        # Nudge the shell to produce its prompt faster
        if self._backend:
            try:
                self._backend.write("\r")
            except Exception:
                pass
        # Trigger initial refresh so the widget isn't invisible
        try:
            self.call_from_thread(self.refresh)
        except Exception:
            pass
        empty_reads = 0
        while self._pty_active and self._backend:
            try:
                data = self._backend.read()
            except Exception:
                data = ""
            if data:
                empty_reads = 0
                try:
                    self._stream.feed(data)
                except Exception:
                    pass
                try:
                    self.call_from_thread(self.refresh)
                except Exception:
                    pass
            else:
                empty_reads += 1
            try:
                if self._backend and not self._backend.is_alive():
                    # Final drain — read any remaining output
                    try:
                        final = self._backend.read()
                        if final and self._stream:
                            self._stream.feed(final)
                    except Exception:
                        pass
                    self._pty_active = False
                    try:
                        self.call_from_thread(self.refresh)
                    except Exception:
                        pass
                    break
            except Exception:
                break
            # Adaptive sleep: faster when getting data, slower when idle
            time.sleep(0.03 if empty_reads < 10 else 0.1)

    def on_key(self, event: Any) -> None:
        """Send keystrokes to the PTY."""
        if not self._pty_active or not self._backend:
            return

        event.stop()
        event.prevent_default()

        key = event.key

        # Ctrl+key combos
        if key.startswith("ctrl+") and len(key) == 6:
            char = key[-1]
            code = ord(char.upper()) - 64
            if 0 < code < 32:
                self._backend.write(chr(code))
                return

        # Special keys
        mapped = _KEY_MAP.get(key)
        if mapped:
            self._backend.write(mapped)
            return

        # Regular character
        if event.character and len(event.character) == 1:
            self._backend.write(event.character)

    def on_resize(self, event: Resize) -> None:
        """Resize the PTY and pyte screen when the widget resizes."""
        new_cols = event.size.width
        new_rows = event.size.height
        if new_cols < 1 or new_rows < 1:
            return
        if new_cols == self._cols and new_rows == self._rows:
            return
        self._cols = new_cols
        self._rows = new_rows
        if self._screen:
            self._screen.resize(self._rows, self._cols)
        if self._backend:
            self._backend.set_size(self._cols, self._rows)

    def render_line(self, y: int) -> Strip:
        """Render a single line of the terminal screen."""
        # Show error message if spawn failed
        if self._spawn_error:
            if y == 1:
                msg = self._spawn_error
                segments = [Segment(msg, Style(color="red", bold=True))]
                pad = self.size.width - len(msg)
                if pad > 0:
                    segments.append(Segment(" " * pad))
                return Strip(segments, self.size.width)
            return Strip.blank(self.size.width)

        if not self._screen or y >= self._screen.lines:
            return Strip.blank(self.size.width)

        line = self._screen.buffer[y]
        segments: list[Segment] = []
        for x in range(self._screen.columns):
            char = line[x]
            ch = char.data if char.data else " "
            style = _char_style(char)
            # Cursor highlight
            if y == self._screen.cursor.y and x == self._screen.cursor.x and self.has_focus:
                style = style + Style(reverse=True)
            segments.append(Segment(ch, style))

        return Strip(segments, self._cols)

    def on_unmount(self) -> None:
        self.stop()
