"""Textual TUI for BookMem.

Design goals:
- persistent spatial layout
- keyboard-first navigation
- progressive help
- safe control panel actions
- useful long-task monitoring
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import asyncio
import json
import subprocess
from typing import Any

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Log,
    Static,
    TabbedContent,
    TabPane,
    TextArea,
)

from . import __version__
from .config import get_settings
from .doctor import run_doctor
from .frontmatter import discover_book_files, read_markdown_with_frontmatter
from .index_versions import index_status
from .search import search_books
from .router import route_query
from .duplicates import load_book_identities, find_duplicate_groups
from .review import review_file_path
from .evaluation import evaluate_retrieval
from .setup_wizard import load_setup_presets, setup_steps_for_preset, setup_status, run_setup_preset


@dataclass
class BookRow:
    title: str
    author: str
    class_code: str
    class_label: str
    path: str


SAFE_COMMANDS: dict[str, list[str]] = {
    "doctor": ["bookmem", "doctor"],
    "doctor --fix": ["bookmem", "doctor", "--fix"],
    "index-status": ["bookmem", "index-status"],
    "build-graph": ["bookmem", "build-graph"],
    "eval retrieval": ["bookmem", "eval", "retrieval"],
    "ingest --changed-only": ["bookmem", "ingest", "--changed-only"],
    "prepare-books --changed-only": ["bookmem", "prepare-books", "data/raw-books", "--changed-only"],
}


class StatusCard(Static):
    """Small dashboard card."""

    def __init__(self, title: str, value: str = "—", detail: str = "", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.title = title
        self.value = value
        self.detail = detail

    def render(self) -> str:
        return f"[b]{self.title}[/b]\n[accent]{self.value}[/accent]\n[dim]{self.detail}[/dim]"


class BookMemTUI(App):
    """BookMem terminal UI."""

    CSS = """
    Screen {
        background: $surface;
        color: $text;
    }

    Header {
        background: $primary;
        color: $text;
    }

    Footer {
        background: $boost;
    }

    #root {
        height: 100%;
    }

    #dashboard-grid {
        height: auto;
        padding: 1;
    }

    StatusCard {
        width: 1fr;
        min-width: 22;
        height: 6;
        border: round $primary;
        padding: 1;
        margin: 0 1 1 0;
        background: $panel;
    }

    .pane {
        border: round $primary;
        padding: 1;
        margin: 0 1 1 0;
        background: $panel;
    }

    .focused-pane {
        border: heavy $accent;
    }

    DataTable {
        height: 1fr;
    }

    TextArea {
        height: 1fr;
        border: round $primary;
    }

    Log {
        height: 1fr;
        border: round $primary;
    }

    Input {
        margin-bottom: 1;
    }

    Button {
        margin: 0 1 1 0;
    }

    #help {
        dock: bottom;
        height: 3;
        background: $boost;
        color: $text-muted;
        padding: 1;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("?", "toggle_help", "Help"),
        ("r", "refresh", "Refresh"),
        ("/", "focus_search", "Search"),
        ("ctrl+d", "dashboard", "Dashboard"),
    ]

    help_visible = reactive(True)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="root"):
            with TabbedContent(id="tabs"):
                with TabPane("Setup", id="setup"):
                    yield Label("First-run setup wizard. Choose a preset, inspect the plan, then run it.")
                    yield DataTable(id="setup-presets-table")
                    with Horizontal():
                        yield Button("Mode: safe", id="setup-mode-safe")
                        yield Button("Mode: repair", id="setup-mode-repair")
                        yield Button("Mode: rebuild", id="setup-mode-rebuild")
                    with Horizontal():
                        yield Button("Use full_fat", id="setup-full_fat")
                        yield Button("Use balanced", id="setup-balanced")
                        yield Button("Use minimal", id="setup-minimal")
                        yield Button("Use import_ready", id="setup-import_ready")
                        yield Button("Use agent_ready", id="setup-agent_ready")
                    yield TextArea("", id="setup-plan", read_only=True)
                    yield Log(id="setup-log")
                with TabPane("Dashboard", id="dashboard"):
                    with Horizontal(id="dashboard-grid"):
                        yield StatusCard("Books", id="books-card")
                        yield StatusCard("Chunks", id="chunks-card")
                        yield StatusCard("Review", id="review-card")
                        yield StatusCard("Index", id="index-card")
                    yield TextArea("", id="dashboard-detail", read_only=True)
                with TabPane("Books", id="books"):
                    yield Input(placeholder="Filter books by title, author, class or topic. Press / to focus search.", id="book-filter")
                    yield DataTable(id="books-table")
                with TabPane("Search", id="search"):
                    yield Input(placeholder="Search corpus, e.g. systems versus goals", id="search-input")
                    yield DataTable(id="search-table")
                    yield TextArea("", id="search-detail", read_only=True)
                with TabPane("Review", id="review"):
                    yield DataTable(id="review-table")
                    yield TextArea("", id="review-detail", read_only=True)
                with TabPane("Duplicates", id="duplicates"):
                    yield DataTable(id="duplicates-table")
                with TabPane("System", id="system"):
                    yield TextArea("", id="system-detail", read_only=True)
                with TabPane("Control", id="control"):
                    yield Label("Safe commands only. Long tasks stream output below.")
                    with Horizontal():
                        for name in SAFE_COMMANDS:
                            yield Button(name, id=f"cmd-{name.replace(' ', '-').replace('--', '')}")
                    yield Log(id="command-log")
            yield Static("[q]uit  [r]efresh  [/]search  [?]help  [Tab]focus  [Enter]select", id="help")
        yield Footer()

    def on_mount(self) -> None:
        self.title = f"BookMem {__version__}"
        self.refresh_all()

    def action_toggle_help(self) -> None:
        self.help_visible = not self.help_visible
        self.query_one("#help", Static).display = self.help_visible

    def action_refresh(self) -> None:
        self.refresh_all()

    def action_dashboard(self) -> None:
        tabs = self.query_one("#tabs", TabbedContent)
        tabs.active = "dashboard"

    def action_focus_search(self) -> None:
        active = self.query_one("#tabs", TabbedContent).active
        if active == "books":
            self.query_one("#book-filter", Input).focus()
        elif active == "search":
            self.query_one("#search-input", Input).focus()
        else:
            self.query_one("#search-input", Input).focus()
            self.query_one("#tabs", TabbedContent).active = "search"

    def refresh_all(self) -> None:
        self.load_dashboard()
        self.load_books()
        self.load_review()
        self.load_duplicates()
        self.load_system()


def load_setup(self) -> None:
    table = self.query_one("#setup-presets-table", DataTable)
    table.clear(columns=True)
    table.add_columns("Preset", "Label", "Description")
    presets = load_setup_presets()
    for name, preset in presets.items():
        table.add_row(name, preset.label, preset.description)
    status = setup_status()
    self.query_one("#setup-plan", TextArea).text = json.dumps(status, indent=2, ensure_ascii=False)

def show_setup_plan(self, preset_name: str) -> None:
    presets = load_setup_presets()
    if preset_name not in presets:
        self.query_one("#setup-plan", TextArea).text = f"Unknown preset: {preset_name}"
        return
    steps = setup_steps_for_preset(presets[preset_name])
    payload = {
        "preset": presets[preset_name].__dict__,
        "steps": [step.__dict__ for step in steps],
    }
    self.query_one("#setup-plan", TextArea).text = json.dumps(payload, indent=2, ensure_ascii=False)

async def run_setup_from_tui(self, preset_name: str) -> None:
    log = self.query_one("#setup-log", Log)
    log.write_line(f"Starting setup preset: {preset_name}")
    self.show_setup_plan(preset_name)

    def callback(step_id: str, message: str) -> None:
        self.call_from_thread(log.write_line, f"[{step_id}] {message}")

    result = await asyncio.to_thread(run_setup_preset, preset_name, False, callback)
    log.write_line("Setup finished.")
    for item in result.get("steps", []):
        step = item.get("step", {})
        log.write_line(f"{item.get('status').upper()}: {step.get('label')}")
    self.refresh_all()

    def load_dashboard(self) -> None:
        doctor = run_doctor(fix=False)
        idx = index_status()
        counts = doctor.get("counts", {})
        self.query_one("#books-card", StatusCard).value = str(counts.get("books", 0))
        self.query_one("#chunks-card", StatusCard).value = str(counts.get("indexed_chunks", 0))
        self.query_one("#review-card", StatusCard).value = str(counts.get("review_items", 0))
        self.query_one("#index-card", StatusCard).value = "STALE" if idx.get("stale") else "OK"
        self.query_one("#index-card", StatusCard).detail = "; ".join(idx.get("reasons") or ["fingerprint OK"])[:80]
        self.query_one("#dashboard-detail", TextArea).text = json.dumps(
            {"doctor": doctor, "index_status": idx},
            indent=2,
            ensure_ascii=False,
        )

    def _book_rows(self) -> list[BookRow]:
        settings = get_settings()
        rows = []
        for path in discover_book_files(settings.books_dir):
            fm, _body, _had = read_markdown_with_frontmatter(path)
            classification = fm.get("classification") if isinstance(fm.get("classification"), dict) else {}
            rows.append(BookRow(
                title=str(fm.get("title") or path.stem),
                author=str(fm.get("author") or ""),
                class_code=str(classification.get("primary_class") or ""),
                class_label=str(classification.get("primary_label") or ""),
                path=str(path),
            ))
        return rows

    def load_books(self, filter_text: str = "") -> None:
        table = self.query_one("#books-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Title", "Author", "Class", "Label", "Path")
        q = filter_text.lower().strip()
        for row in self._book_rows():
            haystack = f"{row.title} {row.author} {row.class_code} {row.class_label} {row.path}".lower()
            if q and q not in haystack:
                continue
            table.add_row(row.title, row.author, row.class_code, row.class_label, row.path)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "book-filter":
            self.load_books(event.value)
        elif event.input.id == "search-input":
            self.run_search(event.value)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "book-filter":
            self.load_books(event.value)

    def run_search(self, query: str) -> None:
        table = self.query_one("#search-table", DataTable)
        detail = self.query_one("#search-detail", TextArea)
        table.clear(columns=True)
        table.add_columns("Book", "Author", "Location", "Citation")
        if not query.strip():
            return
        try:
            route = route_query(query)
            rows = search_books(query, limit=20)
            for row in rows:
                table.add_row(
                    str(row.get("title") or ""),
                    str(row.get("author") or ""),
                    str(row.get("heading_path") or ""),
                    str(row.get("citation") or ""),
                )
            detail.text = json.dumps({
                "route": route.model_dump() if hasattr(route, "model_dump") else getattr(route, "__dict__", str(route)),
                "results": rows[:5],
            }, indent=2, ensure_ascii=False)
        except Exception as exc:
            detail.text = f"Search failed: {exc}"

    def load_review(self) -> None:
        table = self.query_one("#review-table", DataTable)
        detail = self.query_one("#review-detail", TextArea)
        table.clear(columns=True)
        table.add_columns("Queue", "Status", "Path")
        body = {}
        for name in ("needs_metadata.yaml", "needs_classification.yaml", "low_confidence_matches.yaml", "possible_duplicates.yaml"):
            path = review_file_path(name)
            if path.exists():
                text = path.read_text(encoding="utf-8")
                table.add_row(name, "present", str(path))
                body[name] = text[:8000]
            else:
                table.add_row(name, "missing", str(path))
        detail.text = json.dumps(body, indent=2, ensure_ascii=False)

    def load_duplicates(self) -> None:
        table = self.query_one("#duplicates-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Reason", "Book", "Author", "Path")
        try:
            identities = load_book_identities(get_settings().books_dir, include_raw=True)
            groups = find_duplicate_groups(identities, by="isbn")
            for group in groups:
                for book in group.books:
                    table.add_row(group.reason, book.title, book.author or "", str(book.path))
        except Exception as exc:
            table.add_row("error", str(exc), "", "")

    def load_system(self) -> None:
        data = {
            "doctor": run_doctor(fix=False),
            "index_status": index_status(),
        }
        self.query_one("#system-detail", TextArea).text = json.dumps(data, indent=2, ensure_ascii=False)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        label = str(event.button.label)
        if label in SAFE_COMMANDS:
            await self.run_safe_command(label)

    async def run_safe_command(self, label: str) -> None:
        log = self.query_one("#command-log", Log)
        cmd = SAFE_COMMANDS[label]
        log.write_line(f"$ {' '.join(cmd)}")
        log.write_line("Running...")

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(Path.cwd()),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        assert proc.stdout is not None
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            log.write_line(line.decode(errors="replace").rstrip())
        code = await proc.wait()
        log.write_line(f"Command exited with code {code}")


def run_tui() -> None:
    BookMemTUI().run()
