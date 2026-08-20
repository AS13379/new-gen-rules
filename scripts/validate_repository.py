#!/usr/bin/env python3
"""Validate generated profiles and curated rule invariants."""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from pathlib import Path

ALLOWED_RULE_TYPES = {
    "DOMAIN",
    "DOMAIN-SUFFIX",
    "DOMAIN-KEYWORD",
    "IP-CIDR",
    "IP-CIDR6",
    "PROCESS-NAME",
}
BUILTIN_TARGETS = {"DIRECT", "REJECT", "PASS", "REJECT-DROP", "COMPATIBLE"}


def load_generator(root: Path):
    path = root / "scripts" / "build_profiles.py"
    spec = importlib.util.spec_from_file_location(f"profile_generator_{id(root)}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load generator: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def active_rule_lines(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith(("#", ";"))
    ]


def validate_rule_files(root: Path) -> list[str]:
    errors: list[str] = []
    locations: dict[str, Path] = {}
    for path in sorted((root / "rules").rglob("*.list")):
        seen: set[str] = set()
        for number, line in enumerate(active_rule_lines(path), start=1):
            if line in seen:
                errors.append(f"duplicate rule in {path.relative_to(root)}: {line}")
            seen.add(line)
            previous = locations.get(line)
            if previous is not None and previous != path:
                errors.append(
                    "cross-file duplicate rule: "
                    f"{line} in {previous.relative_to(root)} and {path.relative_to(root)}"
                )
            else:
                locations[line] = path
            rule_type = line.split(",", 1)[0]
            if rule_type not in ALLOWED_RULE_TYPES:
                errors.append(
                    f"unsupported rule type in {path.relative_to(root)} line {number}: {rule_type}"
                )
            if "," not in line:
                errors.append(f"malformed rule in {path.relative_to(root)} line {number}: {line}")
    return errors


def protected_adult_domains(root: Path) -> set[str]:
    """Adult content domains are sourced from the proxy list itself.

    rules/proxy/adult-content.list is the single source of truth, so a domain can
    never be protected by the routing rules while being invisible to the guard.
    """
    protected: set[str] = set()
    path = root / "rules" / "proxy" / "adult-content.list"
    for rule in active_rule_lines(path):
        parts = [part.strip() for part in rule.split(",")]
        if len(parts) < 2 or parts[0] not in {"DOMAIN", "DOMAIN-SUFFIX"}:
            continue
        protected.add(parts[1].lower().rstrip("."))
    return protected


def reject_rule_captures(kind: str, value: str, protected: str) -> bool:
    """Report whether a REJECT rule can capture traffic for a protected domain.

    Exact equality is not enough: a broader DOMAIN-SUFFIX or any DOMAIN-KEYWORD
    rule in a reject list would silently block an adult content site.
    """
    if kind == "DOMAIN":
        # Blocks the apex itself or one of its hostnames.
        return value == protected or value.endswith("." + protected)
    if kind == "DOMAIN-SUFFIX":
        # Either direction is a capture: a narrower host, or a broader parent zone.
        return (
            value == protected
            or value.endswith("." + protected)
            or protected.endswith("." + value)
        )
    if kind == "DOMAIN-KEYWORD":
        # A keyword hitting the apex hits every hostname beneath it.
        return value in protected
    return False


def validate_adult_site_separation(root: Path) -> list[str]:
    """Keep adult content classified as content, not as advertising.

    The point is category ownership, not censorship: adult *sites* belong to the
    adult content ruleset so the user can decide in the client whether that group
    proxies or rejects. Adult *ad networks* belong to the reject lists. A site
    silently captured by an ad rule would take that choice away.
    """
    errors: list[str] = []
    protected = protected_adult_domains(root)
    if not protected:
        errors.append("adult content protection list is empty: rules/proxy/adult-content.list")
        return errors

    allow_path = root / "tests" / "fixtures" / "adult-sites-allow.txt"
    declared = {
        line.strip().lower()
        for line in allow_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }
    for domain in sorted(protected - declared):
        errors.append(
            "adult content domain missing from tests/fixtures/adult-sites-allow.txt: " f"{domain}"
        )
    for domain in sorted(declared - protected):
        errors.append(
            "adult-sites-allow.txt lists a domain absent from rules/proxy/adult-content.list: "
            f"{domain}"
        )

    for path in sorted((root / "rules" / "reject").glob("*.list")):
        for rule in active_rule_lines(path):
            parts = [part.strip() for part in rule.split(",")]
            if len(parts) < 2:
                continue
            kind, value = parts[0], parts[1].lower().rstrip(".")
            for domain in sorted(protected):
                if reject_rule_captures(kind, value, domain):
                    errors.append(
                        f"REJECT rule in {path.relative_to(root)} captures adult content "
                        f"domain {domain}: {rule}"
                    )
    return errors


def validate_direct_reject_separation(root: Path) -> list[str]:
    """Adblock profiles load china-services before the reject lists.

    A domain present in both would therefore bypass ad blocking, so the two sets
    must stay disjoint.
    """
    errors: list[str] = []
    direct: dict[str, Path] = {}
    for path in sorted((root / "rules" / "direct").glob("*.list")):
        for rule in active_rule_lines(path):
            parts = [part.strip() for part in rule.split(",")]
            if len(parts) >= 2 and parts[0] in {"DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD"}:
                direct[parts[1].lower().rstrip(".")] = path
    for path in sorted((root / "rules" / "reject").glob("*.list")):
        for rule in active_rule_lines(path):
            parts = [part.strip() for part in rule.split(",")]
            if len(parts) < 2:
                continue
            value = parts[1].lower().rstrip(".")
            for candidate, direct_path in direct.items():
                if value == candidate or value.endswith("." + candidate):
                    errors.append(
                        f"REJECT rule in {path.relative_to(root)} shadows direct rule "
                        f"{candidate} from {direct_path.relative_to(root)}: {rule}"
                    )
    return errors


def validate_ruleset_sources(root: Path) -> list[str]:
    """Every ruleset source must be a builtin or a file under rules/.

    The simulator resolves these paths with `root / source`, so an absolute or
    traversing path would read outside the repository.
    """
    errors: list[str] = []
    builtins = {"[]GEOIP,CN", "[]FINAL"}
    rules_dir = (root / "rules").resolve()
    for path in sorted((root / "profiles").glob("*.ini")):
        for line in active_rule_lines(path):
            if not line.startswith("ruleset="):
                continue
            _, source = line.split("=", 1)[1].split(",", 1)
            if source in builtins:
                continue
            if source.startswith("[]"):
                errors.append(f"{path.relative_to(root)}: unknown builtin ruleset: {source}")
                continue
            candidate = Path(source)
            if candidate.is_absolute() or ".." in candidate.parts:
                errors.append(f"{path.relative_to(root)}: unsafe ruleset path: {source}")
                continue
            resolved = (root / candidate).resolve()
            if not str(resolved).startswith(str(rules_dir) + "/"):
                errors.append(f"{path.relative_to(root)}: ruleset escapes rules/: {source}")
            elif not resolved.is_file():
                errors.append(f"{path.relative_to(root)}: ruleset source missing: {source}")
    return errors


def validate_profiles(root: Path) -> list[str]:
    errors: list[str] = []
    generator = load_generator(root)
    expected = generator.build_all(root)
    profile_dir = root / "profiles"
    actual_names = {path.stem for path in profile_dir.glob("*.ini")}
    if actual_names != set(expected):
        errors.append(
            f"public profile set mismatch: expected {sorted(expected)}, got {sorted(actual_names)}"
        )

    for name, expected_text in expected.items():
        path = profile_dir / f"{name}.ini"
        if not path.exists() or path.read_text(encoding="utf-8") != expected_text:
            errors.append(f"stale generated profile: profiles/{name}.ini")
            continue
        text = expected_text
        groups = {
            line.split("=", 1)[1].split("`", 1)[0]
            for line in text.splitlines()
            if line.startswith("custom_proxy_group=")
        }
        allowed_targets = groups | BUILTIN_TARGETS
        for line in text.splitlines():
            if line.startswith("ruleset="):
                target = line.split("=", 1)[1].split(",", 1)[0]
                if target not in allowed_targets:
                    errors.append(f"{name}: unresolved ruleset target: {target}")
            if line.startswith("custom_proxy_group="):
                for segment in line.split("`")[2:]:
                    if not segment.startswith("[]"):
                        continue
                    member = segment[2:]
                    if member and member not in allowed_targets:
                        errors.append(f"{name}: unresolved group member: {member}")
    return errors


def parse_source_blocks(path: Path):
    blocks = []
    for raw_block in path.read_text(encoding="utf-8").split("[[source]]")[1:]:
        values = {}
        for raw_line in raw_block.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"')
        blocks.append(values)
    return blocks


def validate_source_registry(root: Path) -> list[str]:
    errors: list[str] = []
    seen_ids = set()
    for source in parse_source_blocks(root / "policy" / "sources.toml"):
        source_id = source.get("id", "<missing-id>")
        if source_id in seen_ids:
            errors.append(f"duplicate source id: {source_id}")
        seen_ids.add(source_id)
        if not source.get("license"):
            errors.append(f"source lacks license metadata: {source_id}")
        kind = source.get("kind", "")
        if kind == "third-party-reference":
            revision = source.get("revision", "")
            if not re.fullmatch(r"[0-9a-f]{40}", revision):
                errors.append(f"third-party source lacks immutable revision: {source_id}")
        if kind.startswith("official") and not source.get("retrieved"):
            errors.append(f"official source lacks retrieval date: {source_id}")
    return errors


def validate_repository(root: Path) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    errors.extend(validate_rule_files(root))
    errors.extend(validate_adult_site_separation(root))
    errors.extend(validate_direct_reject_separation(root))
    errors.extend(validate_ruleset_sources(root))
    errors.extend(validate_profiles(root))
    errors.extend(validate_source_registry(root))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    errors = validate_repository(args.root)
    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Repository validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
