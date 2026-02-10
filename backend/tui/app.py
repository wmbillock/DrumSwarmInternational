"""DCI Swarm — Textual TUI Dashboard.

Split-pane layout:
  Left (60%):  Embedded terminal (Claude Code, shell, etc.)
  Right (40%): Six switchable dashboard views + swarm actions modal

Usage:
    python -m backend.tui.app              # default shell
    python -m backend.tui.app -- claude    # launch claude in terminal pane
    ./dci mark-time --tui
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path so dashboard_data can be imported
_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.timer import Timer
from textual.widgets import (
    Footer,
    Header,
    Label,
    Static,
    TabbedContent,
    TabPane,
    Button,
)
from textual.screen import ModalScreen

from scripts.monitoring import dashboard_data
from scripts.monitoring.dashboard_data import (
    get_agent_memory_stats,
    get_agent_roster,
    get_completed_reps,
    get_git_status,
    get_lifecycle_data,
    get_recent_commits,
    get_recent_logs,
    get_service_status,
    get_shows_summary,
)

# Try to import the terminal widget — graceful fallback if deps missing
_HAS_TERMINAL = False
try:
    from backend.tui.terminal_widget import TerminalWidget
    _HAS_TERMINAL = True
except ImportError:
    pass


# ── Reusable card widget ─────────────────────────────────────────────

class StatusCard(Static):
    """A small status indicator card."""

    def __init__(self, label: str, value: str = "—", style_class: str = "") -> None:
        super().__init__()
        self._label = label
        self._value = value
        if style_class:
            self.add_class(style_class)

    def compose(self) -> ComposeResult:
        yield Label(self._label, classes="card-label")
        yield Label(self._value, id=f"card-{self._label.lower().replace(' ', '-')}", classes="card-value")

    def update_value(self, value: str) -> None:
        self._value = value
        try:
            self.query_one(".card-value", Label).update(value)
        except NoMatches:
            pass


# ── Tab content panels ───────────────────────────────────────────────

class MetricsPanel(VerticalScroll):
    """View 1: Service status, show counts, quick reference."""

    def compose(self) -> ComposeResult:
        yield Label("[bold cyan]DCI SWARM[/]", classes="panel-title")
        with Horizontal(classes="status-row"):
            yield StatusCard("Backend", "…", "status-card")
            yield StatusCard("Frontend", "…", "status-card")
        yield Label("", id="metrics-shows", classes="section")
        yield Label("", id="metrics-corps", classes="section")
        yield Static("", id="metrics-quickref", classes="section")

    def refresh_data(self) -> None:
        status = get_service_status()
        be_text = "[green]ON[/]" if status["backend"] else "[red]OFF[/]"
        fe_text = "[green]ON[/]" if status["frontend"] else "[red]OFF[/]"

        try:
            for card in self.query(StatusCard):
                if card._label == "Backend":
                    card.update_value(be_text)
                elif card._label == "Frontend":
                    card.update_value(fe_text)
        except NoMatches:
            pass

        if not status["backend"]:
            self._set_label("metrics-shows", "[dim]Backend offline. Run: ./dci forward-march[/]")
            self._set_label("metrics-corps", "")
            self._set_static("metrics-quickref", _quick_ref_text())
            return

        shows = get_shows_summary()
        shows_text = (
            f"[bold]SHOWS[/]  {shows['total']} total\n"
            f"  [green]Active: {shows['active']}[/]  [yellow]Draft: {shows['draft']}[/]  "
            f"[blue]Done: {shows['completed']}[/]"
        )
        self._set_label("metrics-shows", shows_text)

        corps_lines = []
        for detail in shows["active_details"]:
            corps_lines.append(
                f"  [bold]{detail['corps_name']}[/]  "
                f"Agents: [green]{detail['active_agents']}[/]/{detail['total_agents']}"
            )
        self._set_label("metrics-corps", "\n".join(corps_lines))
        self._set_static("metrics-quickref", _quick_ref_text())

    def _set_label(self, widget_id: str, text: str) -> None:
        try:
            self.query_one(f"#{widget_id}", Label).update(text)
        except NoMatches:
            pass

    def _set_static(self, widget_id: str, text: str) -> None:
        try:
            self.query_one(f"#{widget_id}", Static).update(text)
        except NoMatches:
            pass


class AgentsPanel(VerticalScroll):
    """View 2: Agent hierarchy trees."""

    def compose(self) -> ComposeResult:
        yield Label("[bold green]AGENTS[/]", classes="panel-title")
        yield Static("", id="agents-content")

    def refresh_data(self) -> None:
        rosters = get_agent_roster()
        if not rosters:
            self._set("agents-content", "[dim]No active corps. Create and activate a show.[/]")
            return

        lines: list[str] = []
        for roster_info in rosters:
            status_parts = []
            for s in ["active", "completed", "failed"]:
                count = roster_info["by_status"].get(s, 0)
                if count:
                    icon = _status_icon(s)
                    status_parts.append(f"{icon} {count}")

            lines.append(f"[bold]{roster_info['title']}[/]  {' '.join(status_parts)}")
            lines.append("")

            for root in roster_info["roots"]:
                _render_tree(root, roster_info["by_parent"], 0, lines)
            lines.append("")

        self._set("agents-content", "\n".join(lines))

    def _set(self, widget_id: str, text: str) -> None:
        try:
            self.query_one(f"#{widget_id}", Static).update(text)
        except NoMatches:
            pass


class LogsPanel(VerticalScroll):
    """View 3: Recent backend logs."""

    def compose(self) -> ComposeResult:
        yield Label("[bold yellow]LOGS[/]", classes="panel-title")
        yield Static("", id="logs-content")

    def refresh_data(self) -> None:
        logs = get_recent_logs(50)
        if not logs:
            self._set("logs-content", "[dim]No log file found.[/]")
            return

        lines: list[str] = []
        for entry in logs:
            if entry["is_http"]:
                code = entry["status_code"]
                color = "green" if code.startswith("2") else "red"
                lines.append(f"  [dim]BE[/] [{color}]{code}[/] {entry['method_path']}")
            elif entry["level"] == "error":
                lines.append(f"  [red]{entry['raw'][:120]}[/]")
            elif entry["level"] == "warning":
                lines.append(f"  [yellow]{entry['raw'][:120]}[/]")
            else:
                lines.append(f"  [dim]{entry['raw'][:120]}[/]")

        self._set("logs-content", "\n".join(lines))

    def _set(self, widget_id: str, text: str) -> None:
        try:
            self.query_one(f"#{widget_id}", Static).update(text)
        except NoMatches:
            pass


class ChangesPanel(VerticalScroll):
    """View 4: Git status + recent commits + completed reps."""

    def compose(self) -> ComposeResult:
        yield Label("[bold magenta]CHANGES[/]", classes="panel-title")
        yield Static("", id="changes-git")
        yield Static("", id="changes-commits")
        yield Static("", id="changes-reps")

    def refresh_data(self) -> None:
        git = get_git_status()
        staged = git["staged"]
        unstaged = git["unstaged"]

        if not staged and not unstaged:
            git_text = "  [green]Working tree clean[/]"
        else:
            parts = [f"  [bold]{len(staged) + len(unstaged)} file(s) changed[/]"]
            if staged:
                parts.append("  [green]Staged:[/]")
                for f in staged[:10]:
                    icon = _git_icon(f["status"])
                    path = f["path"] if len(f["path"]) <= 50 else "..." + f["path"][-47:]
                    parts.append(f"    {icon} {path}")
                if len(staged) > 10:
                    parts.append(f"    [dim]... +{len(staged) - 10} more[/]")
            if unstaged:
                parts.append("  [yellow]Unstaged:[/]")
                for f in unstaged[:10]:
                    icon = _git_icon(f["status"])
                    path = f["path"] if len(f["path"]) <= 50 else "..." + f["path"][-47:]
                    parts.append(f"    {icon} {path}")
                if len(unstaged) > 10:
                    parts.append(f"    [dim]... +{len(unstaged) - 10} more[/]")
            git_text = "\n".join(parts)

        self._set("changes-git", git_text)

        commits = get_recent_commits(8)
        if commits:
            commit_lines = ["  [bold]RECENT COMMITS[/]"]
            for c in commits:
                commit_lines.append(f"  [dim]{c['hash']}[/] {c['message'][:50]}")
            self._set("changes-commits", "\n".join(commit_lines))
        else:
            self._set("changes-commits", "")

        reps = get_completed_reps()
        rep_lines = ["  [bold]COMPLETED REPS[/]"]
        if reps:
            for r in reps:
                rep_lines.append(
                    f"  [green]{r['completed']} done[/]  "
                    f"[cyan]{r['pending']} wip[/]  "
                    f"[red]{r['failed']} fail[/]"
                )
        else:
            rep_lines.append("  [dim]No reps yet.[/]")
        self._set("changes-reps", "\n".join(rep_lines))

    def _set(self, widget_id: str, text: str) -> None:
        try:
            self.query_one(f"#{widget_id}", Static).update(text)
        except NoMatches:
            pass


class MemoryPanel(VerticalScroll):
    """View 5: Agent memory statistics."""

    def compose(self) -> ComposeResult:
        yield Label("[bold blue]MEMORY[/]", classes="panel-title")
        yield Static("", id="memory-content")

    def refresh_data(self) -> None:
        data = get_agent_memory_stats()
        if not data:
            self._set("memory-content", "[dim]No active corps.[/]")
            return

        lines: list[str] = []
        for corps_info in data:
            lines.append(f"  [bold]{corps_info['title']}[/]")
            for agent in corps_info["agents"]:
                role = agent["role"].replace("_", " ").title()[:18]
                type_parts = [f"{t}:{c}" for t, c in sorted(agent["by_type"].items())]
                type_str = " ".join(type_parts) if type_parts else "none"
                lines.append(
                    f"    {role:<20} [green]{agent['total_memories']}[/] mem  "
                    f"[cyan]{agent['task_memories']}[/] tasks  "
                    f"conf:{agent['avg_confidence']:.1f}  ({type_str})"
                )
            lines.append("")

        self._set("memory-content", "\n".join(lines))

    def _set(self, widget_id: str, text: str) -> None:
        try:
            self.query_one(f"#{widget_id}", Static).update(text)
        except NoMatches:
            pass


class LifecyclePanel(VerticalScroll):
    """View 6: Corps lifecycle overview."""

    def compose(self) -> ComposeResult:
        yield Label("[bold magenta]LIFECYCLE[/]", classes="panel-title")
        yield Static("", id="lifecycle-content")

    def refresh_data(self) -> None:
        data = get_lifecycle_data()
        if not data:
            self._set("lifecycle-content", "[dim]No active corps.[/]")
            return

        lines: list[str] = []
        for corps in data:
            lines.append(f"  [bold]{corps['title']}[/]  [dim]({corps['mascot']} / {corps['theme']})[/]")
            lines.append("")

            ageouts = corps["ageouts"]
            if ageouts:
                lines.append(f"  [yellow]Pending Ageouts: {len(ageouts)}[/]")
                for a in ageouts[:5]:
                    lines.append(f"    {a.get('name', '?')} — age {a.get('age', '?')}")
            else:
                lines.append("  [green]No pending ageouts[/]")
            lines.append("")

            by_class = corps["by_classification"]
            if by_class:
                lines.append("  [bold]Classification Breakdown[/]")
                class_icons = {
                    "performing_member": "\u266b",
                    "instructional_staff": "\u2691",
                    "administrative_staff": "\u2605",
                    "logistics": "\u2699",
                    "dci_assigned": "\u2696",
                }
                for cls in ["administrative_staff", "instructional_staff", "performing_member", "logistics", "dci_assigned"]:
                    if cls in by_class:
                        icon = class_icons.get(cls, "?")
                        info = by_class[cls]
                        label = cls.replace("_", " ").title()
                        lines.append(f"    {icon} {label}: {info['active']}/{info['total']}")
            lines.append("")

            improvements = corps["pending_improvements"]
            if improvements:
                lines.append(f"  [cyan]Pending Improvements: {len(improvements)}[/]")
                for p in improvements[:5]:
                    lines.append(
                        f"    v{p.get('old_version', '?')}->v{p.get('new_version', '?')}: "
                        f"{p.get('reason', '?')[:40]}"
                    )
            lines.append("")

        self._set("lifecycle-content", "\n".join(lines))

    def _set(self, widget_id: str, text: str) -> None:
        try:
            self.query_one(f"#{widget_id}", Static).update(text)
        except NoMatches:
            pass


# ── Swarm Actions Screen ─────────────────────────────────────────────

class SwarmActionsModal(ModalScreen[str | None]):
    """Modal popup for swarm actions — equivalent to tmux prefix+s menu."""

    BINDINGS = [Binding("escape", "dismiss_modal", "Close")]

    def compose(self) -> ComposeResult:
        with Vertical(id="actions-modal"):
            yield Label("[bold]DCI Swarm Actions[/]", classes="modal-title")
            yield Button("Resume Hut (restart BE+FE)", id="action-resume-hut", variant="primary")
            yield Button("Heartbeat", id="action-heartbeat")
            yield Button("Run-Through (tests)", id="action-run-tests")
            yield Button("Restart Backend", id="action-restart-backend")
            yield Button("Restart Frontend", id="action-restart-frontend")
            yield Button("Run Migration", id="action-migrate")
            yield Button("Check Step (status)", id="action-check-step")
            yield Button("Open Browser", id="action-open-browser")
            yield Button("Parade Rest (stop all)", id="action-parade-rest", variant="error")
            yield Button("Cancel", id="action-cancel", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        action_id = event.button.id
        if action_id == "action-cancel":
            self.dismiss(None)
        else:
            self.dismiss(action_id)

    def action_dismiss_modal(self) -> None:
        self.dismiss(None)


# ── Action Result Screen ─────────────────────────────────────────────

class ActionResultScreen(ModalScreen[None]):
    """Shows the output of a swarm action."""

    BINDINGS = [
        Binding("escape", "dismiss_result", "Close"),
        Binding("enter", "dismiss_result", "Close"),
    ]

    def __init__(self, title: str, output: str) -> None:
        super().__init__()
        self._title = title
        self._output = output

    def compose(self) -> ComposeResult:
        with Vertical(id="result-modal"):
            yield Label(f"[bold]{self._title}[/]", classes="modal-title")
            yield Static(self._output, id="result-output")
            yield Button("OK", id="result-ok", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None)

    def action_dismiss_result(self) -> None:
        self.dismiss(None)


# ── Main App ─────────────────────────────────────────────────────────

class DCISwarmDashboard(App):
    """DCI Swarm — Split-pane TUI: terminal left, dashboard right."""

    TITLE = "DCI Swarm Dashboard"
    SUB_TITLE = "ctrl+b: toggle focus | 1-6: tabs | s: swarm menu | q: quit"

    CSS = """
    Screen {
        background: $surface;
    }

    /* ── Split layout ──────────────────────────────── */

    #split-container {
        height: 1fr;
    }

    #terminal-pane {
        width: 60%;
        border-right: solid $primary-darken-2;
    }

    #dashboard-pane {
        width: 40%;
    }

    /* Dashboard-only mode (no terminal) */
    #dashboard-pane.full-width {
        width: 100%;
    }

    .terminal-unavailable {
        width: 60%;
        padding: 2 4;
        color: $text-muted;
        border-right: solid $primary-darken-2;
    }

    /* ── Modals ─────────────────────────────────────── */

    #actions-modal, #result-modal {
        width: 60;
        max-height: 80%;
        background: $panel;
        border: thick $accent;
        padding: 1 2;
        margin: 2 4;
    }

    #actions-modal Button {
        width: 100%;
        margin-bottom: 1;
    }

    #result-modal {
        width: 80;
    }

    #result-output {
        max-height: 20;
        overflow-y: auto;
        padding: 1;
        background: $surface;
        border: round $primary-lighten-2;
        margin-bottom: 1;
    }

    .modal-title {
        text-align: center;
        padding: 1;
        text-style: bold;
    }

    /* ── Dashboard panels ──────────────────────────── */

    .panel-title {
        padding: 0 1;
        text-style: bold;
        margin-bottom: 1;
    }

    .section {
        padding: 0 1;
        margin-bottom: 1;
    }

    .status-row {
        height: auto;
        padding: 0 1;
        margin-bottom: 1;
    }

    .status-card {
        width: 1fr;
        height: auto;
        padding: 0 1;
        margin-right: 2;
    }

    .card-label {
        text-style: bold;
        color: $text-muted;
    }

    .card-value {
        color: $text;
    }

    TabPane {
        padding: 1;
    }

    TabbedContent {
        height: 1fr;
    }

    /* ── Focus indicator ───────────────────────────── */

    #terminal-pane:focus-within {
        border-right: solid $accent;
    }
    """

    BINDINGS = [
        Binding("ctrl+b", "toggle_focus", "Toggle Focus", show=True, priority=True),
        Binding("1", "switch_tab('metrics')", "Metrics", show=True),
        Binding("2", "switch_tab('agents')", "Agents", show=True),
        Binding("3", "switch_tab('logs')", "Logs", show=True),
        Binding("4", "switch_tab('changes')", "Changes", show=True),
        Binding("5", "switch_tab('memory')", "Memory", show=True),
        Binding("6", "switch_tab('lifecycle')", "Lifecycle", show=True),
        Binding("s", "swarm_menu", "Swarm", show=True),
        Binding("r", "force_refresh", "Refresh", show=True),
        Binding("q", "quit", "Quit", show=True),
    ]

    refresh_timer: Timer | None = None
    _terminal_command: str | None = None
    _cwd: str | None = None
    _show_terminal: bool = False

    def __init__(
        self,
        terminal_command: str | None = None,
        cwd: str | None = None,
        show_terminal: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._terminal_command = terminal_command
        self._cwd = cwd
        self._show_terminal = show_terminal

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="split-container"):
            if self._show_terminal and _HAS_TERMINAL:
                yield TerminalWidget(
                    command=self._terminal_command,
                    cwd=self._cwd,
                    id="terminal-pane",
                )
            with Vertical(id="dashboard-pane", classes="" if self._show_terminal and _HAS_TERMINAL else "full-width"):
                with TabbedContent(id="tabs"):
                    with TabPane("Metrics", id="metrics"):
                        yield MetricsPanel()
                    with TabPane("Agents", id="agents"):
                        yield AgentsPanel()
                    with TabPane("Logs", id="logs"):
                        yield LogsPanel()
                    with TabPane("Changes", id="changes"):
                        yield ChangesPanel()
                    with TabPane("Memory", id="memory"):
                        yield MemoryPanel()
                    with TabPane("Lifecycle", id="lifecycle"):
                        yield LifecyclePanel()
        yield Footer()

    def on_mount(self) -> None:
        dashboard_data.start()
        self.refresh_all_panels()
        self.refresh_timer = self.set_interval(3.0, self.refresh_all_panels)
        # Focus the terminal if it exists
        if self._show_terminal and _HAS_TERMINAL:
            try:
                terminal = self.query_one("#terminal-pane", TerminalWidget)
                terminal.focus()
            except NoMatches:
                pass

    def on_unmount(self) -> None:
        from backend.tui.actions import shutdown_children
        shutdown_children()
        dashboard_data.stop()

    def refresh_all_panels(self) -> None:
        """Read cached data and update the active panel. Instant — never blocks."""
        try:
            tabs = self.query_one("#tabs", TabbedContent)
            active = tabs.active
        except NoMatches:
            active = "metrics"

        panel_map = {
            "metrics": MetricsPanel,
            "agents": AgentsPanel,
            "logs": LogsPanel,
            "changes": ChangesPanel,
            "memory": MemoryPanel,
            "lifecycle": LifecyclePanel,
        }

        panel_class = panel_map.get(active)
        if panel_class:
            try:
                panel = self.query_one(panel_class)
                panel.refresh_data()
            except NoMatches:
                pass

    # ── Actions ───────────────────────────────────────────────────────

    def action_toggle_focus(self) -> None:
        """Toggle focus between terminal and dashboard panes."""
        if not self._show_terminal or not _HAS_TERMINAL:
            return
        try:
            terminal = self.query_one("#terminal-pane", TerminalWidget)
        except NoMatches:
            return

        if terminal.has_focus:
            # Focus the dashboard — pick the first focusable widget in tabs
            try:
                tabs = self.query_one("#tabs", TabbedContent)
                tabs.focus()
            except NoMatches:
                pass
        else:
            terminal.focus()

    def action_switch_tab(self, tab_id: str) -> None:
        try:
            tabs = self.query_one("#tabs", TabbedContent)
            tabs.active = tab_id
            dashboard_data.set_active_tab(tab_id)
            dashboard_data.request_refresh()
            self.refresh_all_panels()
        except NoMatches:
            pass

    def action_force_refresh(self) -> None:
        dashboard_data.request_refresh()
        self.refresh_all_panels()

    def action_swarm_menu(self) -> None:
        self.push_screen(SwarmActionsModal(), callback=self._handle_action)

    def _handle_action(self, action_id: str | None) -> None:
        if action_id is None:
            return
        self._run_swarm_action(action_id)

    @work(thread=True)
    def _run_swarm_action(self, action_id: str) -> None:
        from backend.tui.actions import run_action
        name = action_id.replace("action-", "")
        title, output = run_action(name)
        if name in ("resume-hut", "restart-backend", "restart-frontend", "parade-rest"):
            dashboard_data.reset_cooldowns()
        self.call_from_thread(
            self.push_screen,
            ActionResultScreen(title, output),
        )


# ── Helpers ──────────────────────────────────────────────────────────

def _status_icon(status: str) -> str:
    icons = {
        "active": "[green]\u25cf[/]",
        "completed": "[blue]\u25cb[/]",
        "failed": "[red]\u2717[/]",
        "timed_out": "[magenta]\u23f1[/]",
        "initializing": "[yellow]\u25cc[/]",
        "pending": "[yellow]\u25cc[/]",
        "in_progress": "[cyan]\u25d1[/]",
    }
    return icons.get(status, "?")


def _git_icon(status: str) -> str:
    icons = {
        "M": "[yellow]~[/]",
        "A": "[green]+[/]",
        "D": "[red]-[/]",
        "R": "[blue]>[/]",
        "?": "[dim]?[/]",
    }
    return icons.get(status, "?")


def _render_tree(agent: dict, by_parent: dict, depth: int, lines: list[str]) -> None:
    indent = "  " + "  " * depth
    role = agent.get("role", "?").replace("_", " ").title()
    status = agent.get("status", "?")
    icon = _status_icon(status)
    connector = "\u251c\u2500" if depth > 0 else ""
    lines.append(f"{indent}{connector}{icon} {role}")

    children = by_parent.get(agent.get("id"), [])
    for child in children:
        _render_tree(child, by_parent, depth + 1, lines)


def _quick_ref_text() -> str:
    lines = [
        "[dim]" + "\u2500" * 50 + "[/]",
        "",
        "  [bold]COMMANDS[/]",
    ]
    cmds = [
        ("ten-hut", "Start all"),
        ("parade-rest", "Stop all"),
        ("resume-hut", "Restart services"),
        ("forward-march", "Backend only"),
        ("company-front", "Frontend only"),
        ("run-through", "Tests"),
        ("drill -p N", "Euler drill"),
        ("check-step", "Status"),
    ]
    for cmd, desc in cmds:
        lines.append(f"  [green]{cmd:<16}[/][dim]{desc}[/]")
    lines.append("")
    lines.append("  [bold]URLS[/]")
    lines.append("  Frontend  [cyan]http://localhost:5173[/]")
    lines.append(f"  Backend   [cyan]{get_service_status().get('backend_port', '4224')}[/]")
    return "\n".join(lines)


# ── Entry point ──────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="DCI Swarm TUI Dashboard")
    parser.add_argument(
        "command", nargs="?", default=None,
        help="Command to run in the terminal pane (requires --terminal)",
    )
    parser.add_argument(
        "--terminal", action="store_true",
        help="Enable embedded terminal pane (split view: 60%% terminal, 40%% dashboard)",
    )
    parser.add_argument(
        "--cwd", default=None,
        help="Working directory for the terminal pane",
    )
    args, _ = parser.parse_known_args()

    # Use explicit --cwd, or the project root (from _project_root), or os.getcwd()
    cwd = args.cwd or _project_root

    app = DCISwarmDashboard(
        terminal_command=args.command,
        cwd=cwd,
        show_terminal=args.terminal,
    )
    app.run()


if __name__ == "__main__":
    main()
