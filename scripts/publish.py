#!/usr/bin/env python3
"""生成发布版 Subconverter 外部配置（ruleset 固定到 commit SHA 的 Raw URL）。

背景：Subconverter 的 config 参数对本地文件只接受相对路径——绝对路径会被静默
读空（日志报 `Load external configuration failed: Empty document`），Subconverter
回退到内置默认配置，规则和分组都未生效。本脚本把 ruleset 的相对路径改写为固定
commit 的 Raw URL，配合 `config=<dist/*.ini 的 Raw URL>` 使用，让 config 和规则
都走远程，彻底绕开本地路径问题。

用法：
    python3 scripts/publish.py --ref <commit-sha 或 tag>

生成 dist/*.ini，其 ruleset 指向 <ref>/rules/... 的 Raw URL。
建议用 tag 作为 ref（生产不应追踪 main）。
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

RAW_BASE = "https://raw.githubusercontent.com/AS13379/new-gen-rules"
FULL_SHA_RE = re.compile(r"[0-9a-fA-F]{40}")
VERSION_TAG_RE = re.compile(r"v[0-9][0-9A-Za-z._-]*")
MOVING_REFS = {"head", "main", "master"}


def resolve_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def validate_ref(ref: str) -> str:
    value = ref.strip()
    if value.lower() in MOVING_REFS:
        raise ValueError(f"生产发布禁止使用可移动引用: {value}")
    if not (FULL_SHA_RE.fullmatch(value) or VERSION_TAG_RE.fullmatch(value)):
        raise ValueError("ref 必须是 40 位 commit SHA，或以 v 开头的版本标签")
    return value


def render_profiles(ref: str, root: Path) -> dict[str, str]:
    ref = validate_ref(ref)
    src_dir = root / "profiles"
    rendered: dict[str, str] = {}
    for ini in sorted(src_dir.glob("*.ini")):
        text = ini.read_text(encoding="utf-8")
        # 只改写以 rules/ 开头的相对路径；[]GEOIP,CN、[]FINAL 等特殊规则保留
        new_text = re.sub(
            r"ruleset=([^,\n]+),(rules/[^\n]+)",
            lambda m: f"ruleset={m.group(1)},{RAW_BASE}/{ref}/{m.group(2)}",
            text,
        )
        rendered[ini.name] = new_text
    return rendered


def publish(ref: str, root: Path) -> dict[str, str]:
    ref = validate_ref(ref)
    out_dir = root / "dist"
    out_dir.mkdir(parents=True, exist_ok=True)
    rendered = render_profiles(ref, root)
    published: dict[str, str] = {}
    for name, text in rendered.items():
        (out_dir / name).write_text(text, encoding="utf-8")
        published[name] = f"{RAW_BASE}/{ref}/dist/{name}"
    (out_dir / "RELEASE_REF").write_text(ref + "\n", encoding="utf-8")
    return published


def check_published(ref: str, root: Path) -> list[str]:
    ref = validate_ref(ref)
    out_dir = root / "dist"
    errors: list[str] = []
    release_ref = out_dir / "RELEASE_REF"
    if not release_ref.exists() or release_ref.read_text(encoding="utf-8").strip() != ref:
        errors.append("dist/RELEASE_REF 与检查的 ref 不一致")
    for name, expected in render_profiles(ref, root).items():
        path = out_dir / name
        if not path.exists():
            errors.append(f"缺少发布文件: dist/{name}")
        elif path.read_text(encoding="utf-8") != expected:
            errors.append(f"发布文件已过期: dist/{name}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", help="commit SHA 或 tag，默认当前 HEAD")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--check", action="store_true", help="只检查 dist 是否与指定 ref 一致，不写文件")
    args = parser.parse_args()
    try:
        ref = validate_ref(args.ref or resolve_head())
    except ValueError as error:
        parser.error(str(error))
    if args.check:
        errors = check_published(ref, args.root)
        if errors:
            print("发布制品检查失败:", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            return 1
        print(f"发布制品与 {ref} 一致: 6")
        return 0
    published = publish(ref, args.root)
    print(f"已生成 {len(published)} 份发布版配置（ruleset 固定到 {ref[:7]}）:")
    for name, url in published.items():
        print(f"  {name}")
    print()
    print("落地用法（Subconverter，config 用远程 URL）:")
    print(f"  config={published['Full.ini']}")
    print("  完整示例: /sub?target=clash&url=<节点订阅>&config=" + published["Full.ini"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
