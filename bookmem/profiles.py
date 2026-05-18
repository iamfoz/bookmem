"""Config profiles / environments for BookMem."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, asdict
from pathlib import Path
import os
from typing import Any, Iterator

import yaml


PROFILES_VERSION = "0.1.0"
PROFILES_DIR = Path("config/profiles")
CURRENT_PROFILE_PATH = Path("data/manifests/current_profile.yaml")


@dataclass
class ConfigProfile:
    name: str
    label: str
    description: str
    environment: str
    path: str
    data_dir: str
    config_dir: str
    exports_dir: str
    backups_dir: str
    lancedb_dir: str
    api_host: str | None
    api_port: int | None
    api_require_key: bool
    mcp_enabled: bool
    default_workspace: str | None
    default_limit: int
    permissions_profile: str | None
    require_confirmation_for_writes: bool
    auto_restore_points: bool
    audit_log: bool
    plugins_enabled: bool


def profile_files() -> list[Path]:
    if not PROFILES_DIR.exists():
        return []
    return sorted(PROFILES_DIR.glob("*.yaml")) + sorted(PROFILES_DIR.glob("*.yml"))


def load_profile_file(path: Path) -> ConfigProfile:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Profile must be a YAML mapping: {path}")

    profile = data.get("profile") if isinstance(data.get("profile"), dict) else {}
    paths = data.get("paths") if isinstance(data.get("paths"), dict) else {}
    services = data.get("services") if isinstance(data.get("services"), dict) else {}
    api = services.get("api") if isinstance(services.get("api"), dict) else {}
    mcp = services.get("mcp") if isinstance(services.get("mcp"), dict) else {}
    retrieval = data.get("retrieval") if isinstance(data.get("retrieval"), dict) else {}
    agent = data.get("agent") if isinstance(data.get("agent"), dict) else {}
    features = data.get("features") if isinstance(data.get("features"), dict) else {}

    name = str(profile.get("name") or path.stem)

    return ConfigProfile(
        name=name,
        label=str(profile.get("label") or name),
        description=str(profile.get("description") or ""),
        environment=str(profile.get("environment") or name),
        path=str(path),
        data_dir=str(paths.get("data_dir") or "data"),
        config_dir=str(paths.get("config_dir") or "config"),
        exports_dir=str(paths.get("exports_dir") or "exports"),
        backups_dir=str(paths.get("backups_dir") or "backups"),
        lancedb_dir=str(paths.get("lancedb_dir") or "data/lancedb"),
        api_host=str(api.get("host")) if api.get("host") is not None else None,
        api_port=int(api.get("port")) if api.get("port") is not None else None,
        api_require_key=bool(api.get("require_api_key", False)),
        mcp_enabled=bool(mcp.get("enabled", False)),
        default_workspace=str(retrieval.get("default_workspace")) if retrieval.get("default_workspace") else None,
        default_limit=int(retrieval.get("default_limit") or 10),
        permissions_profile=str(agent.get("permissions_profile")) if agent.get("permissions_profile") else None,
        require_confirmation_for_writes=bool(agent.get("require_confirmation_for_writes", True)),
        auto_restore_points=bool(features.get("auto_restore_points", True)),
        audit_log=bool(features.get("audit_log", True)),
        plugins_enabled=bool(features.get("plugins_enabled", False)),
    )


def load_profiles() -> dict[str, ConfigProfile]:
    profiles: dict[str, ConfigProfile] = {}
    for path in profile_files():
        profile = load_profile_file(path)
        profiles[profile.name] = profile
    return profiles


def get_profile(name: str | None = None) -> ConfigProfile:
    name = name or active_profile_name() or "local"
    profiles = load_profiles()
    if name not in profiles:
        raise KeyError(f"Unknown profile: {name}")
    return profiles[name]


def active_profile_name() -> str | None:
    env = os.environ.get("BOOKMEM_PROFILE")
    if env:
        return env
    if CURRENT_PROFILE_PATH.exists():
        data = yaml.safe_load(CURRENT_PROFILE_PATH.read_text(encoding="utf-8")) or {}
        if isinstance(data, dict) and data.get("profile"):
            return str(data.get("profile"))
    return None


def write_current_profile(name: str) -> None:
    # Validate first.
    get_profile(name)
    CURRENT_PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CURRENT_PROFILE_PATH.write_text(
        yaml.safe_dump({"schema_version": 1, "profile": name}, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


@contextmanager
def profile_environment(profile_name: str | None) -> Iterator[ConfigProfile | None]:
    if not profile_name:
        yield None
        return

    profile = get_profile(profile_name)
    env_updates = {
        "BOOKMEM_PROFILE": profile.name,
        "BOOKMEM_DATA_DIR": profile.data_dir,
        "BOOKMEM_CONFIG_DIR": profile.config_dir,
        "BOOKMEM_EXPORTS_DIR": profile.exports_dir,
        "BOOKMEM_BACKUPS_DIR": profile.backups_dir,
        "BOOKMEM_LANCEDB_DIR": profile.lancedb_dir,
        "BOOKMEM_AGENT_PERMISSIONS_PROFILE": profile.permissions_profile or "",
    }

    old = {key: os.environ.get(key) for key in env_updates}
    try:
        for key, value in env_updates.items():
            if value:
                os.environ[key] = value
        yield profile
    finally:
        for key, value in old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def validate_profile(name: str) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    try:
        profile = get_profile(name)
    except Exception as exc:
        return [{"level": "error", "issue": "load", "message": str(exc)}]

    for attr in ("data_dir", "config_dir", "exports_dir", "backups_dir", "lancedb_dir"):
        value = getattr(profile, attr)
        if not value:
            issues.append({"level": "error", "issue": attr, "message": f"{attr} is required."})

    if profile.api_port is not None and not (1 <= profile.api_port <= 65535):
        issues.append({"level": "error", "issue": "api_port", "message": "API port must be between 1 and 65535."})

    if profile.permissions_profile:
        perm_path = Path(profile.config_dir) / "agent_permissions.yaml"
        if not perm_path.exists() and profile.config_dir == "config":
            issues.append({"level": "warn", "issue": "permissions_profile", "message": "Permissions profile is set but config/agent_permissions.yaml was not found."})

    if profile.default_limit < 1:
        issues.append({"level": "error", "issue": "default_limit", "message": "default_limit must be at least 1."})

    return issues


def profiles_as_dict() -> list[dict[str, Any]]:
    return [asdict(profile) for profile in load_profiles().values()]


def profile_as_dict(profile: ConfigProfile) -> dict[str, Any]:
    return asdict(profile)
