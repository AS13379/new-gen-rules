#!/usr/bin/env python3
"""Generate Subconverter external configs from one policy model."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

PROFILE_NAMES = (
    "Full",
    "Full_Adblock",
    "Standard",
    "Standard_Adblock",
    "Mini",
    "Mini_Adblock",
)

AUTO_URL = "https://www.gstatic.com/generate_204"


@dataclass(frozen=True)
class ProfileSpec:
    tier: str
    adblock: bool


SPECS = {
    name: ProfileSpec(
        tier=name.split("_", 1)[0].lower(),
        adblock=name.endswith("_Adblock"),
    )
    for name in PROFILE_NAMES
}


def ruleset(target: str, source: str) -> str:
    return f"ruleset={target},{source}"


def select_group(
    name: str,
    *members: str,
    include_all: bool = False,
    nodes_after: int | None = None,
) -> str:
    entries = [f"`[]{member}" for member in members]
    if include_all:
        position = len(entries) if nodes_after is None else nodes_after
        entries.insert(position, "`.*")
    return f"custom_proxy_group={name}`select{''.join(entries)}"


def auto_group() -> str:
    return f"custom_proxy_group=♻️ 自动选择`url-test`.*`{AUTO_URL}`300,,50"


def rule_target(
    tier: str,
    *,
    full: str | None = None,
    standard: str | None = None,
    mini: str | None = None,
) -> str:
    if tier == "full" and full:
        return full
    if tier == "standard" and standard:
        return standard
    if tier == "mini" and mini:
        return mini
    return "🚀 节点选择"


def render_rules(spec: ProfileSpec) -> list[str]:
    tier = spec.tier
    lines = [
        ruleset("🎯 中国直连", "rules/direct/private.list"),
        ruleset("🎯 中国直连", "rules/direct/china-services.list"),
    ]
    if spec.adblock:
        lines.extend(
            [
                ruleset("🛑 广告拦截", "rules/reject/ads-base.list"),
            ]
        )
    lines.extend(
        [
            ruleset(rule_target(tier, full="🍎 Apple服务", standard="🍎 Apple服务"), "rules/proxy/apple.list"),
            ruleset(rule_target(tier, full="📢 谷歌服务", standard="📢 谷歌服务"), "rules/proxy/google.list"),
            ruleset(rule_target(tier, full="📲 通讯社交", standard="📲 通讯社交"), "rules/proxy/messaging.list"),
            ruleset(rule_target(tier, full="💬 AI平台", standard="💬 AI平台"), "rules/proxy/ai.list"),
            ruleset(rule_target(tier, full="🎥 流媒体", standard="🎥 流媒体"), "rules/proxy/youtube.list"),
            ruleset(rule_target(tier, full="🎥 流媒体", standard="🎥 流媒体"), "rules/proxy/streaming.list"),
            ruleset(rule_target(tier, full="💹 加密货币"), "rules/proxy/crypto.list"),
            ruleset(rule_target(tier, full="🎮 游戏平台"), "rules/proxy/games.list"),
            ruleset(rule_target(tier, full="Ⓜ️ Microsoft服务", standard="Ⓜ️ Microsoft服务"), "rules/proxy/microsoft.list"),
            ruleset(rule_target(tier, full="💻 开发者服务"), "rules/proxy/developer.list"),
            ruleset(rule_target(tier, full="🔞 成人内容"), "rules/proxy/adult-content.list"),
            ruleset(
                rule_target(tier, full="📺 哔哩哔哩", standard="🎯 中国直连", mini="🎯 中国直连"),
                "rules/proxy/bilibili.list",
            ),
            ruleset(rule_target(tier), "rules/proxy/meta.list"),
            ruleset("🎯 中国直连", "[]GEOIP,CN"),
            ruleset("🐟 漏网之鱼", "[]FINAL"),
        ]
    )
    return lines


def service_group(name: str, *, allow_reject: bool = False) -> str:
    """Build a selectable policy group.

    `allow_reject` appends REJECT as a selectable option so the user can decide
    in the client whether the category is proxied or blocked. The default stays
    proxied; the choice is exposed, never made here.
    """
    members = ["🚀 节点选择", "♻️ 自动选择", "DIRECT"]
    if allow_reject:
        members.append("REJECT")
    return select_group(name, *members, include_all=True, nodes_after=2)


def render_groups(spec: ProfileSpec) -> list[str]:
    tier = spec.tier
    if tier == "mini":
        groups = [
            select_group("🚀 节点选择", "♻️ 自动选择", "DIRECT", include_all=True, nodes_after=0),
            auto_group(),
            select_group("🎯 中国直连", "DIRECT", "♻️ 自动选择", "🚀 节点选择"),
            select_group("🐟 漏网之鱼", "🚀 节点选择", "♻️ 自动选择", "DIRECT", "REJECT", include_all=True, nodes_after=2),
        ]
    else:
        groups = [
            select_group("🚀 节点选择", "♻️ 自动选择", "DIRECT", include_all=True, nodes_after=0),
            auto_group(),
            service_group("📢 谷歌服务"),
            service_group("🍎 Apple服务"),
            service_group("💬 AI平台"),
            service_group("📲 通讯社交"),
            service_group("🎥 流媒体"),
            service_group("Ⓜ️ Microsoft服务"),
        ]
        if tier == "full":
            groups.extend(
                [
                    select_group("📺 哔哩哔哩", "DIRECT", "♻️ 自动选择", "🚀 节点选择", include_all=True),
                    service_group("💹 加密货币"),
                    service_group("🎮 游戏平台"),
                    service_group("💻 开发者服务"),
                    service_group("🔞 成人内容", allow_reject=True),
                ]
            )
        groups.extend(
            [
                select_group("🎯 中国直连", "DIRECT", "♻️ 自动选择", "🚀 节点选择"),
                select_group("🐟 漏网之鱼", "🚀 节点选择", "♻️ 自动选择", "DIRECT", "REJECT", include_all=True, nodes_after=2),
            ]
        )
    if spec.adblock:
        groups.append(select_group("🛑 广告拦截", "REJECT", "DIRECT"))
    return groups


def render_profile(name: str) -> str:
    spec = SPECS[name]
    header = [
        "[custom]",
        "; Generated by scripts/build_profiles.py. Do not edit directly.",
        f"; Profile: {name}",
        "enable_rule_generator=true",
        "overwrite_original_rules=true",
        "",
    ]
    sections = header + render_rules(spec) + [""] + render_groups(spec) + [""]
    return "\n".join(sections)


def build_all(root: Path) -> dict[str, str]:
    del root  # Reserved for future source-manifest validation.
    return {name: render_profile(name) for name in PROFILE_NAMES}


def write_profiles(root: Path) -> dict[str, str]:
    profiles = build_all(root)
    output_dir = root / "profiles"
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, content in profiles.items():
        (output_dir / f"{name}.ini").write_text(content, encoding="utf-8")
    return profiles


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if generated profiles differ")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    expected = build_all(args.root)
    if args.check:
        mismatches = []
        for name, content in expected.items():
            path = args.root / "profiles" / f"{name}.ini"
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                mismatches.append(str(path))
        if mismatches:
            print("Generated profiles are stale:")
            for path in mismatches:
                print(f"- {path}")
            return 1
        print(f"Profiles are current: {len(expected)}")
        return 0
    write_profiles(args.root)
    print(f"Generated profiles: {len(expected)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
