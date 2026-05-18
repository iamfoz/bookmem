"""Explicit migration system for BookMem.

Migrations are separate from doctor --fix. Doctor diagnoses and performs
conservative repairs only; migrations change persisted schema/metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from importlib import util
from pathlib import Path
import json
import re
from typing import Any


MIGRATION_SYSTEM_VERSION = "0.1.0"
MIGRATIONS_DIR = Path("migrations")
MIGRATION_STATE_PATH = Path("data/manifests/migrations.json")


@dataclass
class Migration:
    id: str
    description: str
    path: str
    applied: bool
    applied_at: str | None = None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def migration_state_path() -> Path:
    return MIGRATION_STATE_PATH


def load_migration_state() -> dict[str, Any]:
    path = migration_state_path()
    if not path.exists():
        return {
            "schema_version": 1,
            "migration_system_version": MIGRATION_SYSTEM_VERSION,
            "applied": [],
        }
    return json.loads(path.read_text(encoding="utf-8"))


def save_migration_state(state: dict[str, Any]) -> None:
    path = migration_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def migration_files() -> list[Path]:
    if not MIGRATIONS_DIR.exists():
        return []
    return sorted(
        path for path in MIGRATIONS_DIR.glob("[0-9][0-9][0-9][0-9]_*.py")
        if path.is_file()
    )


def load_migration_module(path: Path):
    module_name = f"bookmem_migration_{path.stem}"
    spec = util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load migration: {path}")
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def applied_lookup(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    applied = state.get("applied", [])
    if not isinstance(applied, list):
        return {}
    return {
        str(item.get("id")): item
        for item in applied
        if isinstance(item, dict) and item.get("id")
    }


def list_migrations() -> list[Migration]:
    state = load_migration_state()
    applied = applied_lookup(state)
    migrations = []

    for path in migration_files():
        module = load_migration_module(path)
        migration_id = str(getattr(module, "ID", path.stem))
        applied_item = applied.get(migration_id)
        migrations.append(
            Migration(
                id=migration_id,
                description=str(getattr(module, "DESCRIPTION", "")),
                path=str(path),
                applied=applied_item is not None,
                applied_at=applied_item.get("applied_at") if applied_item else None,
            )
        )
    return migrations


def migration_status() -> dict[str, Any]:
    migrations = list_migrations()
    pending = [m for m in migrations if not m.applied]
    return {
        "schema_version": 1,
        "migration_system_version": MIGRATION_SYSTEM_VERSION,
        "state_path": str(migration_state_path()),
        "migrations_dir": str(MIGRATIONS_DIR),
        "total": len(migrations),
        "applied": len([m for m in migrations if m.applied]),
        "pending": len(pending),
        "migrations": [asdict(m) for m in migrations],
    }


def apply_migrations(dry_run: bool = False, target: str | None = None) -> dict[str, Any]:
    state = load_migration_state()
    applied = applied_lookup(state)
    migrations = []

    for path in migration_files():
        module = load_migration_module(path)
        migration_id = str(getattr(module, "ID", path.stem))
        if migration_id in applied:
            continue
        migrations.append((path, module, migration_id))
        if target and migration_id == target:
            break

    if dry_run:
        return {
            "dry_run": True,
            "applied": [],
            "pending_to_apply": [
                {
                    "id": migration_id,
                    "path": str(path),
                    "description": str(getattr(module, "DESCRIPTION", "")),
                }
                for path, module, migration_id in migrations
            ],
        }

    state.setdefault("schema_version", 1)
    state["migration_system_version"] = MIGRATION_SYSTEM_VERSION
    state.setdefault("applied", [])

    results = []
    for path, module, migration_id in migrations:
        if not hasattr(module, "apply"):
            raise AttributeError(f"Migration {migration_id} has no apply(context) function.")

        context = {
            "root": str(Path.cwd()),
            "migration_id": migration_id,
            "migration_path": str(path),
        }
        result = module.apply(context)  # type: ignore[attr-defined]
        record = {
            "id": migration_id,
            "path": str(path),
            "description": str(getattr(module, "DESCRIPTION", "")),
            "applied_at": utc_now_iso(),
            "result": result,
        }
        state["applied"].append(record)
        save_migration_state(state)
        results.append(record)

    return {
        "dry_run": False,
        "applied": results,
        "pending_to_apply": [],
        "state_path": str(migration_state_path()),
    }


def slugify_migration_name(name: str) -> str:
    value = name.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return re.sub(r"_+", "_", value).strip("_") or "migration"


def next_migration_number() -> int:
    max_num = 0
    for path in migration_files():
        match = re.match(r"^(\d{4})_", path.name)
        if match:
            max_num = max(max_num, int(match.group(1)))
    return max_num + 1


def create_migration(name: str) -> dict[str, Any]:
    MIGRATIONS_DIR.mkdir(parents=True, exist_ok=True)
    number = next_migration_number()
    slug = slugify_migration_name(name)
    migration_id = f"{number:04d}_{slug}"
    path = MIGRATIONS_DIR / f"{migration_id}.py"

    if path.exists():
        raise FileExistsError(f"Migration already exists: {path}")

    title = name.strip().replace('"', '\\"')
    template = (
        f'"""{migration_id}\\n\\n{title}\\n"""\\n\\n'
        "from __future__ import annotations\\n\\n"
        "from pathlib import Path\\n"
        "from typing import Any\\n\\n\\n"
        f'ID = "{migration_id}"\\n'
        f'DESCRIPTION = "{title}"\\n'
        "VERSION = 1\\n\\n\\n"
        "def apply(context: dict[str, Any]) -> dict[str, Any]:\\n"
        '    root = Path(context.get("root", "."))\\n'
        "    # TODO: implement migration.\\n"
        "    # Keep migrations idempotent. Do not overwrite human-reviewed metadata unless\\n"
        "    # the migration is explicitly designed and documented to do so.\\n"
        '    return {"changed": False, "note": "Migration stub created; implement apply()."}\\n'
    )
    path.write_text(template, encoding="utf-8")

    return {
        "id": migration_id,
        "path": str(path),
        "description": title,
    }
