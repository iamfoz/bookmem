"""Prompt pack assets for BookMem."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import re
from typing import Any


PROMPTS_DIR = Path("prompts")


@dataclass
class PromptAsset:
    name: str
    path: str
    title: str
    description: str


def prompt_name_from_path(path: Path) -> str:
    return path.stem


def _first_heading(text: str) -> str:
    for line in text.splitlines():
        match = re.match(r"^#\s+(.+?)\s*$", line)
        if match:
            return match.group(1).strip()
    return ""


def _description(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    for index, line in enumerate(lines):
        if line.lower() == "## purpose":
            for candidate in lines[index + 1:]:
                if candidate and not candidate.startswith("#"):
                    return candidate
    for line in lines:
        if line and not line.startswith("#"):
            return line
    return ""


def list_prompts(prompts_dir: Path | None = None) -> list[PromptAsset]:
    prompts_dir = prompts_dir or PROMPTS_DIR
    if not prompts_dir.exists():
        return []

    prompts = []
    for path in sorted(prompts_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        prompts.append(
            PromptAsset(
                name=prompt_name_from_path(path),
                path=str(path),
                title=_first_heading(text) or path.stem,
                description=_description(text),
            )
        )
    return prompts


def prompt_path(name: str, prompts_dir: Path | None = None) -> Path:
    prompts_dir = prompts_dir or PROMPTS_DIR
    candidate = prompts_dir / f"{name}.md"
    if candidate.exists():
        return candidate
    # Allow exact filename too.
    exact = prompts_dir / name
    if exact.exists():
        return exact
    raise FileNotFoundError(f"Prompt not found: {name}")


def show_prompt(name: str, prompts_dir: Path | None = None) -> str:
    return prompt_path(name, prompts_dir=prompts_dir).read_text(encoding="utf-8")


def prompt_assets_as_dict(prompts: list[PromptAsset]) -> list[dict[str, Any]]:
    return [asdict(prompt) for prompt in prompts]
