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
from pathlib import Path

RAW_BASE = "https://raw.githubusercontent.com/AS13379/new-gen-rules"


def resolve_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def publish(ref: str, root: Path) -> dict[str, str]:
    src_dir = root / "profiles"
    out_dir = root / "dist"
    out_dir.mkdir(parents=True, exist_ok=True)
    published: dict[str, str] = {}
    for ini in sorted(src_dir.glob("*.ini")):
        text = ini.read_text(encoding="utf-8")
        # 只改写以 rules/ 开头的相对路径；[]GEOIP,CN、[]FINAL 等特殊规则保留
        new_text = re.sub(
            r"ruleset=([^,\n]+),(rules/[^\n]+)",
            lambda m: f"ruleset={m.group(1)},{RAW_BASE}/{ref}/{m.group(2)}",
            text,
        )
        (out_dir / ini.name).write_text(new_text, encoding="utf-8")
        published[ini.name] = f"{RAW_BASE}/{ref}/dist/{ini.name}"
    return published


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", help="commit SHA 或 tag，默认当前 HEAD")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    ref = args.ref or resolve_head()
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
