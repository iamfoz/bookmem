"""Agent permissions and safety policy for BookMem."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import fnmatch
from typing import Any

import yaml


PERMISSIONS_VERSION = "0.1.0"
DEFAULT_POLICY_PATH = Path("config/agent_permissions.yaml")

DECISION_ALLOW = "allow"
DECISION_REQUIRE_CONFIRMATION = "require_confirmation"
DECISION_DENY = "deny"
DECISION_UNKNOWN = "unknown"


@dataclass
class PermissionDecision:
    agent: str
    action: str
    decision: str
    matched_rule: str | None
    source: str
    reason: str


def load_permissions(path: Path | None = None) -> dict[str, Any]:
    path = path or DEFAULT_POLICY_PATH
    if not path.exists():
        return {
            "schema_version": 1,
            "defaults": {"allow": [], "require_confirmation": [], "deny": []},
            "agents": {},
        }
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Permissions policy must be a mapping: {path}")
    data.setdefault("defaults", {"allow": [], "require_confirmation": [], "deny": []})
    data.setdefault("agents", {})
    return data


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value]
    if value:
        return [str(value)]
    return []


def _matches(action: str, rules: list[str]) -> str | None:
    for rule in rules:
        if rule == "*" or rule == action or fnmatch.fnmatch(action, rule):
            return rule
    return None


def merged_agent_policy(agent: str, policy: dict[str, Any] | None = None) -> dict[str, Any]:
    policy = policy or load_permissions()
    defaults = policy.get("defaults") if isinstance(policy.get("defaults"), dict) else {}
    agents = policy.get("agents") if isinstance(policy.get("agents"), dict) else {}
    agent_policy = agents.get(agent)
    if not isinstance(agent_policy, dict):
        agent_policy = {}

    merged = {
        "description": agent_policy.get("description", ""),
        "allow": _list(defaults.get("allow")) + _list(agent_policy.get("allow")),
        "require_confirmation": _list(defaults.get("require_confirmation")) + _list(agent_policy.get("require_confirmation")),
        "deny": _list(defaults.get("deny")) + _list(agent_policy.get("deny")),
        "agent_exists": agent in agents,
    }

    # Preserve order but dedupe.
    for key in ("allow", "require_confirmation", "deny"):
        seen = set()
        out = []
        for item in merged[key]:
            if item not in seen:
                seen.add(item)
                out.append(item)
        merged[key] = out

    return merged


def check_permission(agent: str, action: str, policy_path: Path | None = None) -> PermissionDecision:
    policy = load_permissions(policy_path)
    merged = merged_agent_policy(agent, policy)

    # Deny wins.
    matched = _matches(action, merged["deny"])
    if matched:
        return PermissionDecision(
            agent=agent,
            action=action,
            decision=DECISION_DENY,
            matched_rule=matched,
            source="agent/default deny",
            reason=f"Action matched deny rule: {matched}",
        )

    matched = _matches(action, merged["require_confirmation"])
    if matched:
        return PermissionDecision(
            agent=agent,
            action=action,
            decision=DECISION_REQUIRE_CONFIRMATION,
            matched_rule=matched,
            source="agent/default require_confirmation",
            reason=f"Action requires confirmation due to rule: {matched}",
        )

    matched = _matches(action, merged["allow"])
    if matched:
        return PermissionDecision(
            agent=agent,
            action=action,
            decision=DECISION_ALLOW,
            matched_rule=matched,
            source="agent/default allow",
            reason=f"Action allowed by rule: {matched}",
        )

    return PermissionDecision(
        agent=agent,
        action=action,
        decision=DECISION_UNKNOWN,
        matched_rule=None,
        source="no match",
        reason="No permission rule matched. Treat as not allowed until configured.",
    )


def list_agent_permissions(agent: str, policy_path: Path | None = None) -> dict[str, Any]:
    policy = load_permissions(policy_path)
    merged = merged_agent_policy(agent, policy)
    return {
        "agent": agent,
        "description": merged.get("description"),
        "agent_exists": merged.get("agent_exists"),
        "allow": merged["allow"],
        "require_confirmation": merged["require_confirmation"],
        "deny": merged["deny"],
        "permissions_version": PERMISSIONS_VERSION,
    }


def list_agents(policy_path: Path | None = None) -> list[dict[str, Any]]:
    policy = load_permissions(policy_path)
    agents = policy.get("agents") if isinstance(policy.get("agents"), dict) else {}
    out = []
    for name, cfg in sorted(agents.items()):
        cfg = cfg if isinstance(cfg, dict) else {}
        out.append(
            {
                "agent": name,
                "description": cfg.get("description", ""),
                "allow_count": len(_list(cfg.get("allow"))),
                "require_confirmation_count": len(_list(cfg.get("require_confirmation"))),
                "deny_count": len(_list(cfg.get("deny"))),
            }
        )
    return out


def validate_permissions(policy_path: Path | None = None) -> list[dict[str, str]]:
    policy = load_permissions(policy_path)
    issues: list[dict[str, str]] = []

    if policy.get("schema_version") != 1:
        issues.append({"level": "warn", "issue": "schema_version", "message": "Expected schema_version: 1."})

    for section_name in ("defaults",):
        section = policy.get(section_name)
        if not isinstance(section, dict):
            issues.append({"level": "error", "issue": section_name, "message": f"{section_name} must be a mapping."})
            continue
        for key in ("allow", "require_confirmation", "deny"):
            if key in section and not isinstance(section.get(key), list):
                issues.append({"level": "error", "issue": f"{section_name}.{key}", "message": "Must be a list."})

    agents = policy.get("agents")
    if not isinstance(agents, dict):
        issues.append({"level": "error", "issue": "agents", "message": "agents must be a mapping."})
        return issues

    for agent, section in agents.items():
        if not isinstance(section, dict):
            issues.append({"level": "error", "issue": f"agents.{agent}", "message": "Agent policy must be a mapping."})
            continue
        for key in ("allow", "require_confirmation", "deny"):
            if key in section and not isinstance(section.get(key), list):
                issues.append({"level": "error", "issue": f"agents.{agent}.{key}", "message": "Must be a list."})

        allow = set(_list(section.get("allow")))
        deny = set(_list(section.get("deny")))
        overlap = sorted(allow & deny)
        if overlap:
            issues.append({"level": "warn", "issue": f"agents.{agent}.overlap", "message": f"Rules appear in both allow and deny; deny wins: {', '.join(overlap)}"})

    return issues


def decision_as_dict(decision: PermissionDecision) -> dict[str, Any]:
    return asdict(decision)
