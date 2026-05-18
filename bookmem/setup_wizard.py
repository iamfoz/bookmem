"""First-run setup wizard and presets for BookMem."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json
import os
import subprocess
import sys
from typing import Any, Callable

import yaml

from .doctor import run_doctor
from .config import get_settings
from .index_versions import index_status


SETUP_WIZARD_VERSION = "0.1.0"

REQUIRED_DIRS = [
    Path("data/books"),
    Path("data/raw-books"),
    Path("data/lancedb"),
    Path("data/manifests"),
    Path("data/review"),
    Path("data/summaries"),
    Path("data/notes"),
    Path("data/concepts"),
    Path("data/graphs"),
    Path("exports"),
    Path("backups"),
    Path("config/cleaning_profiles.d"),
    Path("config/embedding_models.d"),
    Path("config/summary_providers.d"),
]


@dataclass
class SetupStep:
    id: str
    label: str
    command: list[str] | None
    enabled: bool
    long_running: bool = False
    description: str | None = None


@dataclass
class SetupPreset:
    name: str
    label: str
    description: str
    actions: dict[str, bool]
    summary_provider: str
    embedding_profile: str


def load_setup_presets() -> dict[str, SetupPreset]:
    path = Path("config/setup_presets.yaml")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    presets_raw = (data or {}).get("setup_presets", {})
    if not presets_raw:
        presets_raw = {
            "balanced": {
                "label": "Balanced",
                "description": "Recommended first run.",
                "actions": {"create_dirs": True, "validate_config": True, "doctor_fix": True, "index_status": True},
                "summary_provider": "deterministic",
                "embedding_profile": "default",
            }
        }

    presets = {}
    for name, raw in presets_raw.items():
        presets[name] = SetupPreset(
            name=name,
            label=str(raw.get("label") or name),
            description=str(raw.get("description") or ""),
            actions=dict(raw.get("actions") or {}),
            summary_provider=str(raw.get("summary_provider") or "deterministic"),
            embedding_profile=str(raw.get("embedding_profile") or "default"),
        )
    return presets


def setup_steps_for_preset(preset: SetupPreset) -> list[SetupStep]:
    actions = preset.actions
    return [
        SetupStep("create_dirs", "Create required directories", None, actions.get("create_dirs", True), False, "Create data/config/export folders and .gitkeep placeholders."),
        SetupStep("validate_config", "Validate configuration", ["bookmem", "doctor"], actions.get("validate_config", True), False, "Run doctor to validate environment and configuration."),
        SetupStep("doctor_fix", "Apply safe doctor fixes", ["bookmem", "doctor", "--fix"], actions.get("doctor_fix", True), False, "Create missing folders/placeholders/empty manifest where safe."),
        SetupStep("prepare_changed_only", "Prepare changed raw books", ["bookmem", "prepare-books", "data/raw-books", "--changed-only"], actions.get("prepare_changed_only", False), True, "Clean/classify/canonicalise changed raw Markdown books."),
        SetupStep("ingest_changed_only", "Ingest changed books", ["bookmem", "ingest", "--changed-only"], actions.get("prepare_changed_only", False), True, "Create/update LanceDB index for changed books."),
        SetupStep("clean_check_samples", "Run clean-check on samples", ["bookmem", "clean-check", "data/books"], actions.get("clean_check_samples", False), False, "Reserved for future sample clean-check batch."),
        SetupStep("summarise", "Generate summaries", ["bookmem", "summarise-books", "data/books", "--provider", preset.summary_provider], actions.get("summarise", False), True, "Create book/chapter summary maps."),
        SetupStep("extract_concepts", "Extract concepts", ["bookmem", "concepts", "extract-books", "data/books"], actions.get("extract_concepts", False), True, "Extract reusable models/frameworks/concepts."),
        SetupStep("build_graph", "Build relationship graph", ["bookmem", "build-graph"], actions.get("build_graph", False), False, "Build data/graphs/book_graph.json."),
        SetupStep("eval_retrieval", "Run retrieval evaluation", ["bookmem", "eval", "retrieval"], actions.get("eval_retrieval", False), False, "Run eval/queries.yaml benchmark."),
        SetupStep("index_status", "Check index status", ["bookmem", "index-status"], actions.get("index_status", True), False, "Report index staleness and fingerprint."),
    ]


def create_required_dirs() -> dict[str, Any]:
    created = []
    for path in REQUIRED_DIRS:
        existed = path.exists()
        path.mkdir(parents=True, exist_ok=True)
        gitkeep = path / ".gitkeep"
        if not gitkeep.exists() and path.name not in {"backups", "exports"}:
            gitkeep.write_text("", encoding="utf-8")
        if not existed:
            created.append(str(path))
    return {"created": created, "count": len(created)}


def setup_status() -> dict[str, Any]:
    presets = load_setup_presets()
    doctor = run_doctor(fix=False)
    idx = index_status()
    dirs = {str(path): path.exists() for path in REQUIRED_DIRS}
    return {
        "setup_wizard_version": SETUP_WIZARD_VERSION,
        "presets": [asdict(preset) for preset in presets.values()],
        "doctor": doctor,
        "index_status": idx,
        "directories": dirs,
    }


def run_command_step(command: list[str]) -> dict[str, Any]:
    proc = subprocess.run(command, cwd=Path.cwd(), capture_output=True, text=True)
    return {
        "command": command,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "ok": proc.returncode == 0,
    }


def run_setup_preset(
    preset_name: str,
    dry_run: bool = False,
    status_callback: Callable[[str, str], None] | None = None,
) -> dict[str, Any]:
    presets = load_setup_presets()
    if preset_name not in presets:
        raise KeyError(f"Unknown setup preset: {preset_name}")

    preset = presets[preset_name]
    steps = setup_steps_for_preset(preset)
    results = []

    for step in steps:
        if not step.enabled:
            results.append({"step": asdict(step), "status": "skipped", "result": None})
            continue

        if status_callback:
            status_callback(step.id, f"Starting: {step.label}")

        if dry_run:
            results.append({"step": asdict(step), "status": "planned", "result": None})
            continue

        try:
            if step.id == "create_dirs":
                result = create_required_dirs()
            elif step.id == "clean_check_samples":
                # Placeholder: batch clean-check needs a dedicated implementation later.
                result = {"ok": True, "message": "Skipped: sample clean-check batch is reserved for a future implementation."}
            elif step.command:
                result = run_command_step(step.command)
            else:
                result = {"ok": True}

            status = "ok" if result.get("ok", True) or step.id == "create_dirs" else "failed"
            results.append({"step": asdict(step), "status": status, "result": result})
        except Exception as exc:
            results.append({"step": asdict(step), "status": "failed", "result": {"error": str(exc)}})
            if status_callback:
                status_callback(step.id, f"Failed: {exc}")
            break

        if status_callback:
            status_callback(step.id, f"Finished: {step.label}")

    return {
        "preset": asdict(preset),
        "dry_run": dry_run,
        "steps": results,
        "final_status": setup_status() if not dry_run else None,
    }


def presets_as_dict() -> list[dict[str, Any]]:
    return [asdict(item) for item in load_setup_presets().values()]
