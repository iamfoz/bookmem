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


RERUN_MODES = {"safe", "repair", "rebuild"}


@dataclass
class SetupStep:
    id: str
    label: str
    command: list[str] | None
    enabled: bool
    long_running: bool = False
    description: str | None = None
    rerunnable: bool = True
    destructive: bool = False
    skip_when_existing: bool = False


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



def setup_steps_for_preset(preset: SetupPreset, rerun_mode: str = "safe") -> list[SetupStep]:
    actions = preset.actions
    rebuild = rerun_mode == "rebuild"

    prepare_enabled = actions.get("prepare_changed_only", False)
    ingest_enabled = actions.get("prepare_changed_only", False)
    summarise_enabled = actions.get("summarise", False)
    concepts_enabled = actions.get("extract_concepts", False)
    graph_enabled = actions.get("build_graph", False)
    eval_enabled = actions.get("eval_retrieval", False)

    return [
        SetupStep(
            "create_dirs",
            "Create required directories",
            None,
            actions.get("create_dirs", True),
            False,
            "Create data/config/export folders and .gitkeep placeholders.",
            rerunnable=True,
        ),
        SetupStep(
            "validate_config",
            "Validate configuration",
            ["bookmem", "doctor"],
            actions.get("validate_config", True),
            False,
            "Run doctor to validate environment and configuration.",
            rerunnable=True,
        ),
        SetupStep(
            "doctor_fix",
            "Apply safe doctor fixes",
            ["bookmem", "doctor", "--fix"],
            actions.get("doctor_fix", True),
            False,
            "Create missing folders/placeholders/empty manifest where safe.",
            rerunnable=True,
        ),
        SetupStep(
            "prepare_changed_only",
            "Prepare changed raw books",
            ["bookmem", "prepare-books", "data/raw-books", "--changed-only"],
            prepare_enabled,
            True,
            "Clean/classify/canonicalise changed raw Markdown books.",
            rerunnable=True,
        ),
        SetupStep(
            "ingest_changed_only",
            "Ingest changed books",
            ["bookmem", "ingest", "--changed-only"] if not rebuild else ["bookmem", "ingest", "--reset"],
            ingest_enabled,
            True,
            "Create/update LanceDB index for changed books. Rebuild mode uses --reset.",
            rerunnable=True,
            destructive=rebuild,
        ),
        SetupStep(
            "clean_check_samples",
            "Run clean-check on samples",
            ["bookmem", "clean-check", "data/books"],
            actions.get("clean_check_samples", False),
            False,
            "Reserved for future sample clean-check batch.",
            rerunnable=True,
        ),
        SetupStep(
            "summarise",
            "Generate summaries",
            ["bookmem", "summarise-books", "data/books", "--provider", preset.summary_provider],
            summarise_enabled,
            True,
            "Create book/chapter summary maps.",
            rerunnable=True,
        ),
        SetupStep(
            "extract_concepts",
            "Extract concepts",
            ["bookmem", "concepts", "extract-books", "data/books"],
            concepts_enabled,
            True,
            "Extract reusable models/frameworks/concepts.",
            rerunnable=True,
        ),
        SetupStep(
            "build_graph",
            "Build relationship graph",
            ["bookmem", "build-graph"],
            graph_enabled,
            False,
            "Build data/graphs/book_graph.json.",
            rerunnable=True,
        ),
        SetupStep(
            "eval_retrieval",
            "Run retrieval evaluation",
            ["bookmem", "eval", "retrieval"],
            eval_enabled,
            False,
            "Run eval/queries.yaml benchmark.",
            rerunnable=True,
        ),
        SetupStep(
            "index_status",
            "Check index status",
            ["bookmem", "index-status"],
            actions.get("index_status", True),
            False,
            "Report index staleness and fingerprint.",
            rerunnable=True,
        ),
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



def setup_preflight(preset_name: str = "balanced", rerun_mode: str = "safe") -> dict[str, Any]:
    presets = load_setup_presets()
    if preset_name not in presets:
        raise KeyError(f"Unknown setup preset: {preset_name}")
    if rerun_mode not in RERUN_MODES:
        raise ValueError(f"Unknown rerun mode: {rerun_mode}")

    status = setup_status()
    steps = setup_steps_for_preset(presets[preset_name], rerun_mode=rerun_mode)

    enabled_steps = [step for step in steps if step.enabled]
    long_steps = [step for step in enabled_steps if step.long_running]
    destructive_steps = [step for step in enabled_steps if step.destructive]

    warnings = []
    doctor_status = status.get("doctor", {}).get("status")
    if doctor_status == "FAIL":
        warnings.append("Doctor currently reports FAIL. Prefer `repair` mode or inspect `bookmem doctor` before heavy setup.")
    if destructive_steps:
        warnings.append("Rebuild mode includes reset/rebuild steps. This may recreate generated indexes but should not delete canonical books.")
    if rerun_mode == "safe":
        warnings.append("Safe mode uses changed-only/generated-safe operations where possible.")

    return {
        "preset": preset_name,
        "rerun_mode": rerun_mode,
        "enabled_steps": [asdict(step) for step in enabled_steps],
        "long_running_steps": [asdict(step) for step in long_steps],
        "destructive_steps": [asdict(step) for step in destructive_steps],
        "warnings": warnings,
        "status": status,
    }


def should_skip_step_on_rerun(step: SetupStep, rerun_mode: str) -> tuple[bool, str | None]:
    """Return whether to skip an enabled step for an existing setup."""
    if rerun_mode == "rebuild":
        return False, None

    if step.id == "summarise" and Path("data/summaries").exists() and any(Path("data/summaries").glob("*/book.yaml")):
        if rerun_mode == "safe":
            return True, "summaries already exist; safe mode skips regeneration"
    if step.id == "extract_concepts" and Path("data/concepts/concepts.json").exists():
        if rerun_mode == "safe":
            return True, "concept index already exists; safe mode skips regeneration"
    if step.id == "build_graph" and Path("data/graphs/book_graph.json").exists():
        if rerun_mode == "safe":
            return True, "book graph already exists; safe mode skips rebuild"
    if step.id == "eval_retrieval" and rerun_mode == "safe":
        # Evaluation is harmless, but not required for a sane rerun unless requested.
        return False, None
    return False, None



def run_setup_preset(
    preset_name: str,
    dry_run: bool = False,
    rerun_mode: str = "safe",
    force: bool = False,
    status_callback: Callable[[str, str], None] | None = None,
) -> dict[str, Any]:
    presets = load_setup_presets()
    if preset_name not in presets:
        raise KeyError(f"Unknown setup preset: {preset_name}")
    if rerun_mode not in RERUN_MODES:
        raise ValueError(f"Unknown rerun mode: {rerun_mode}")

    preset = presets[preset_name]
    steps = setup_steps_for_preset(preset, rerun_mode=rerun_mode)
    preflight = setup_preflight(preset_name, rerun_mode=rerun_mode)
    results = []

    for step in steps:
        if not step.enabled:
            results.append({"step": asdict(step), "status": "disabled", "result": None})
            continue

        skip, skip_reason = should_skip_step_on_rerun(step, rerun_mode)
        if skip and not force:
            results.append({"step": asdict(step), "status": "skipped_existing", "result": {"reason": skip_reason}})
            if status_callback:
                status_callback(step.id, f"Skipped: {step.label} ({skip_reason})")
            continue

        if status_callback:
            status_callback(step.id, f"Starting: {step.label}")

        if dry_run:
            results.append({"step": asdict(step), "status": "planned", "result": {"rerun_mode": rerun_mode}})
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
        "rerun_mode": rerun_mode,
        "force": force,
        "dry_run": dry_run,
        "preflight": preflight,
        "steps": results,
        "final_status": setup_status() if not dry_run else None,
    }



def presets_as_dict() -> list[dict[str, Any]]:
    return [asdict(item) for item in load_setup_presets().values()]
