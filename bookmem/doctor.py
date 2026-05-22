"""BookMem health checks and conservative auto-fixes."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from importlib import metadata
from pathlib import Path
import json
import sys
from typing import Any

import yaml

from . import __version__
from .config import get_settings
from .taxonomy import load_taxonomy
from .clean import load_cleaning_profiles, validate_cleaning_profiles
from .citation_exports import validate_citation_styles, validate_reference_export_formats
from .frontmatter import discover_book_files, read_frontmatter_and_body
from .manifest import load_manifest, manifest_path
from .review import review_file_path


STATUS_OK = "OK"
STATUS_WARN = "WARN"
STATUS_FAIL = "FAIL"


REQUIRED_PACKAGES = [
    "lancedb",
    "sentence-transformers",
    "typer",
    "rich",
    "pydantic",
    "python-dotenv",
    "pyarrow",
    "pandas",
    "yaml",
    "fastapi",
    "uvicorn",
    "mcp",
]


CONFIG_FILES = [
    Path("config/bmdc.yaml"),
    Path("config/citation_styles.yaml"),
    Path("config/reference_export_formats.yaml"),
    Path("config/cleaning_profiles.yaml"),
    Path("config/note_templates.yaml"),
]


DATA_DIRS = [
    Path("data/books"),
    Path("data/raw-books"),
    Path("data/lancedb"),
    Path("data/manifests"),
    Path("data/review"),
    Path("data/summaries"),
    Path("data/notes"),
]


@dataclass
class DoctorCheck:
    name: str
    status: str
    message: str
    fixable: bool = False
    fixed: bool = False


def _package_available(package: str) -> bool:
    if package == "yaml":
        try:
            import yaml as _yaml  # noqa: F401
            return True
        except Exception:
            return False

    package_name = package
    # distribution names differ from import names in a few cases
    if package == "sentence-transformers":
        package_name = "sentence-transformers"
    elif package == "python-dotenv":
        package_name = "python-dotenv"
    elif package == "uvicorn":
        package_name = "uvicorn"
    elif package == "mcp":
        package_name = "mcp"

    try:
        metadata.version(package_name)
        return True
    except metadata.PackageNotFoundError:
        # Fallback to import for editable/dev situations.
        import_name = package.replace("-", "_").split("[")[0]
        try:
            __import__(import_name)
            return True
        except Exception:
            return False


def _status_from_children(children: list[DoctorCheck]) -> str:
    if any(check.status == STATUS_FAIL for check in children):
        return STATUS_FAIL
    if any(check.status == STATUS_WARN for check in children):
        return STATUS_WARN
    return STATUS_OK


def _touch_gitkeep(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    gitkeep = path / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.write_text("", encoding="utf-8")


def check_environment() -> DoctorCheck:
    minimum = (3, 11)
    if sys.version_info < minimum:
        return DoctorCheck(
            "Environment",
            STATUS_FAIL,
            f"Python {sys.version.split()[0]} found; Python {minimum[0]}.{minimum[1]}+ required.",
        )
    return DoctorCheck("Environment", STATUS_OK, f"Python {sys.version.split()[0]}; BookMem {__version__}.")


def check_dependencies() -> DoctorCheck:
    missing = [package for package in REQUIRED_PACKAGES if not _package_available(package)]
    if missing:
        return DoctorCheck(
            "Dependencies",
            STATUS_FAIL,
            "Missing required packages: " + ", ".join(missing),
            fixable=False,
        )
    return DoctorCheck("Dependencies", STATUS_OK, "Required packages available.")


def check_config_files(fix: bool = False) -> DoctorCheck:
    missing = [path for path in CONFIG_FILES if not path.exists()]
    fixed = False

    if missing and fix:
        for path in missing:
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.write_text("# TODO: restore BookMem configuration for this file.\n", encoding="utf-8")
                fixed = True
        missing = [path for path in CONFIG_FILES if not path.exists()]

    if missing:
        return DoctorCheck(
            "Config",
            STATUS_FAIL,
            "Missing config files: " + ", ".join(str(path) for path in missing),
            fixable=True,
            fixed=fixed,
        )

    return DoctorCheck("Config", STATUS_OK, "Config files present.", fixable=False, fixed=fixed)


def check_data_dirs(fix: bool = False) -> DoctorCheck:
    missing = [path for path in DATA_DIRS if not path.exists()]
    fixed = False

    if missing and fix:
        for path in missing:
            _touch_gitkeep(path)
            fixed = True
        missing = [path for path in DATA_DIRS if not path.exists()]

    if missing:
        return DoctorCheck(
            "Data folders",
            STATUS_WARN,
            "Missing data folders: " + ", ".join(str(path) for path in missing),
            fixable=True,
            fixed=fixed,
        )

    return DoctorCheck("Data folders", STATUS_OK, "Data folders present.", fixed=fixed)


def check_taxonomy() -> DoctorCheck:
    try:
        taxonomy = load_taxonomy()
    except Exception as exc:
        return DoctorCheck("Taxonomy", STATUS_FAIL, f"Taxonomy failed to load: {exc}")

    classes = taxonomy.get("classes", {}) if isinstance(taxonomy, dict) else {}
    if not classes:
        return DoctorCheck("Taxonomy", STATUS_FAIL, "No taxonomy classes found.")
    return DoctorCheck("Taxonomy", STATUS_OK, f"{len(classes)} taxonomy classes loaded.")


def check_cleaning_profiles() -> DoctorCheck:
    try:
        profiles = load_cleaning_profiles()
        issues = validate_cleaning_profiles()
    except Exception as exc:
        return DoctorCheck("Cleaning profiles", STATUS_FAIL, f"Cleaning profiles failed to load: {exc}")

    if issues:
        return DoctorCheck("Cleaning profiles", STATUS_FAIL, f"{len(issues)} validation issue(s).")
    return DoctorCheck("Cleaning profiles", STATUS_OK, f"{len(profiles)} cleaning profile(s) loaded.")


def _validation_message(issues: list[dict[str, str]]) -> str:
    """Summarise validation issues, naming the first few specifics."""
    detail = "; ".join(
        f"{issue.get('style') or issue.get('format') or '?'} "
        f"({issue.get('message') or issue.get('issue') or 'invalid'})"
        for issue in issues[:3]
    )
    return f"{len(issues)} validation issue(s): {detail}"


def check_citation_styles() -> DoctorCheck:
    try:
        issues = validate_citation_styles()
    except Exception as exc:
        return DoctorCheck("Citation styles", STATUS_FAIL, f"Citation styles failed to load: {exc}")

    if issues:
        return DoctorCheck("Citation styles", STATUS_FAIL, _validation_message(issues))
    return DoctorCheck("Citation styles", STATUS_OK, "Citation styles valid.")


def check_reference_formats() -> DoctorCheck:
    try:
        issues = validate_reference_export_formats()
    except Exception as exc:
        return DoctorCheck("Reference formats", STATUS_FAIL, f"Reference export formats failed to load: {exc}")

    if issues:
        return DoctorCheck("Reference formats", STATUS_FAIL, _validation_message(issues))
    return DoctorCheck("Reference formats", STATUS_OK, "Reference export formats valid.")


def check_manifest(fix: bool = False) -> DoctorCheck:
    path = manifest_path()
    fixed = False

    if not path.exists() and fix:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"schema_version": 1, "books": []}, indent=2), encoding="utf-8")
        fixed = True

    if not path.exists():
        return DoctorCheck("Manifest", STATUS_WARN, f"Manifest not found: {path}", fixable=True, fixed=fixed)

    try:
        manifest = load_manifest()
    except Exception as exc:
        return DoctorCheck("Manifest", STATUS_FAIL, f"Manifest unreadable: {exc}", fixed=fixed)

    books = manifest.get("books", []) if isinstance(manifest, dict) else []
    return DoctorCheck("Manifest", STATUS_OK, f"Manifest readable; {len(books)} record(s).", fixed=fixed)


def check_lancedb() -> DoctorCheck:
    settings = get_settings()
    if not settings.db_dir.exists():
        return DoctorCheck("LanceDB", STATUS_WARN, f"LanceDB directory not found: {settings.db_dir}")

    try:
        import lancedb

        db = lancedb.connect(str(settings.db_dir))
        table_names = db.table_names()
        if settings.table_name not in table_names:
            return DoctorCheck("LanceDB", STATUS_WARN, f"Table not found: {settings.table_name}")
        table = db.open_table(settings.table_name)
        count = table.count_rows()
        return DoctorCheck("LanceDB", STATUS_OK, f"Table {settings.table_name} readable; {count} chunk row(s).")
    except Exception as exc:
        return DoctorCheck("LanceDB", STATUS_FAIL, f"LanceDB unreadable: {exc}")


def collection_counts() -> dict[str, int]:
    settings = get_settings()
    books = discover_book_files(settings.books_dir)
    unclassified = 0
    no_author = 0

    for path in books:
        fm, _body = read_frontmatter_and_body(path)
        classification = fm.get("classification", {}) if isinstance(fm.get("classification"), dict) else {}
        if not classification.get("primary_class") or str(classification.get("primary_class")) == "999":
            unclassified += 1
        if not fm.get("author"):
            no_author += 1

    indexed_chunks = 0
    try:
        import lancedb

        settings = get_settings()
        db = lancedb.connect(str(settings.db_dir))
        if settings.table_name in db.table_names():
            indexed_chunks = db.open_table(settings.table_name).count_rows()
    except Exception:
        indexed_chunks = 0

    review_items = 0
    for name in (
        "metadata",
        "classification",
        "low_confidence",
    ):
        path = review_file_path(name)
        if not path.exists():
            continue
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if isinstance(data, dict):
                for value in data.values():
                    if isinstance(value, list):
                        review_items += len(value)
                if "items" in data and isinstance(data["items"], list):
                    review_items += len(data["items"])
            elif isinstance(data, list):
                review_items += len(data)
        except Exception:
            review_items += 1

    possible_duplicates = review_file_path("low_confidence").parent / "possible_duplicates.yaml"
    if possible_duplicates.exists():
        try:
            data = yaml.safe_load(possible_duplicates.read_text(encoding="utf-8")) or {}
            if isinstance(data, dict):
                for value in data.values():
                    if isinstance(value, list):
                        review_items += len(value)
                if "items" in data and isinstance(data["items"], list):
                    review_items += len(data["items"])
            elif isinstance(data, list):
                review_items += len(data)
        except Exception:
            review_items += 1

    return {
        "books": len(books),
        "indexed_chunks": indexed_chunks,
        "unclassified": unclassified,
        "books_without_author": no_author,
        "review_items": review_items,
    }


def run_doctor(fix: bool = False) -> dict[str, Any]:
    checks = [
        check_environment(),
        check_dependencies(),
        check_config_files(fix=fix),
        check_data_dirs(fix=fix),
        check_taxonomy(),
        check_cleaning_profiles(),
        check_citation_styles(),
        check_reference_formats(),
        check_manifest(fix=fix),
        check_lancedb(),
    ]

    counts = collection_counts()
    status = _status_from_children(checks)

    reasons = []
    for check in checks:
        if check.status != STATUS_OK:
            reasons.append(f"{check.name}: {check.message}")
    if counts["review_items"]:
        if status == STATUS_OK:
            status = STATUS_WARN
        reasons.append(f"{counts['review_items']} review item(s) need attention.")
    if counts["unclassified"]:
        if status == STATUS_OK:
            status = STATUS_WARN
        reasons.append(f"{counts['unclassified']} unclassified book(s).")

    return {
        "bookmem_version": __version__,
        "python_version": sys.version.split()[0],
        "status": status,
        "checks": [asdict(check) for check in checks],
        "counts": counts,
        "reasons": reasons,
        "fixed": [asdict(check) for check in checks if check.fixed],
    }
