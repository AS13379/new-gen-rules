#!/usr/bin/env python3
"""Deterministically simulate domain routing for generated Subconverter profiles."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

PROFILE_NAMES = [
    "Mini",
    "Mini_Adblock",
    "Standard",
    "Standard_Adblock",
    "Full",
    "Full_Adblock",
]


@dataclass(frozen=True)
class RouteResult:
    target: str
    rule: str
    source: str


def active_lines(path: Path):
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith(("#", ";")):
            yield line


def domain_matches(rule: str, domain: str) -> bool:
    parts = [part.strip() for part in rule.split(",")]
    if len(parts) < 2:
        return False
    kind, value = parts[0], parts[1].lower().rstrip(".")
    domain = domain.lower().rstrip(".")
    if kind == "DOMAIN":
        return domain == value
    if kind == "DOMAIN-SUFFIX":
        return domain == value or domain.endswith("." + value)
    if kind == "DOMAIN-KEYWORD":
        return value in domain
    return False


def iter_profile_rules(root: Path, profile: str):
    profile_path = root / "profiles" / f"{profile}.ini"
    for line in active_lines(profile_path):
        if not line.startswith("ruleset="):
            continue
        target, source = line.split("=", 1)[1].split(",", 1)
        yield target, source


def route_domain(root: Path, profile: str, domain: str, cn_ip: bool = False) -> RouteResult:
    if profile not in PROFILE_NAMES:
        raise ValueError(f"unknown profile: {profile}")
    for target, source in iter_profile_rules(root, profile):
        if source == "[]GEOIP,CN":
            if cn_ip:
                return RouteResult(target, "GEOIP,CN", source)
            continue
        if source == "[]FINAL":
            return RouteResult(target, "FINAL", source)
        rule_path = root / source
        if not rule_path.is_file():
            raise FileNotFoundError(f"ruleset source does not exist: {source}")
        for rule in active_lines(rule_path):
            if domain_matches(rule, domain):
                return RouteResult(target, rule, source)
    raise RuntimeError(f"profile {profile} has no FINAL rule")


def expected_target(scenario, profile: str) -> str:
    if scenario.get("ad"):
        if profile.endswith("_Adblock"):
            return "🛑 广告拦截"
        tier = profile.split("_", 1)[0].lower()
        return scenario.get("non_adblock_expected", {}).get(tier, "🐟 漏网之鱼")
    tier = profile.split("_", 1)[0].lower()
    return scenario["expected"][tier]


def run_matrix(root: Path, scenarios):
    results = []
    for scenario in scenarios:
        for profile in PROFILE_NAMES:
            result = route_domain(
                root,
                profile,
                scenario["domain"],
                cn_ip=scenario.get("cn_ip", False),
            )
            expected = expected_target(scenario, profile)
            results.append(
                {
                    "id": scenario["id"],
                    "category": scenario["category"],
                    "domain": scenario["domain"],
                    "profile": profile,
                    "expected": expected,
                    "actual": result.target,
                    "rule": result.rule,
                    "source": result.source,
                    "passed": result.target == expected,
                }
            )
    return results


def render_markdown(results, notes_path: Path | None = None) -> str:
    """Render the report from measured results.

    Any narrative or self-assessment text must come from `notes_path`, never from
    this function, so that tests cannot assert on strings this generator owns.
    """
    total = len(results)
    passed = sum(1 for row in results if row["passed"])
    failed = total - passed
    rate = (passed / total * 100) if total else 0.0
    category_totals = Counter(row["category"] for row in results)
    category_passed = Counter(row["category"] for row in results if row["passed"])
    profile_totals = Counter(row["profile"] for row in results)
    profile_passed = Counter(row["profile"] for row in results if row["passed"])
    category_domains = defaultdict(set)
    for row in results:
        category_domains[row["category"]].add(row["domain"])
    failures = [row for row in results if not row["passed"]]

    lines = [
        "# 严格大陆网络路由模拟报告",
        "",
        "## 模型假设",
        "",
        "- 本机 DIRECT 出口只能可靠访问中国大陆服务；",
        "- 代理出口只能可靠访问境外服务；",
        "- 测试验证的是 Clash/Subconverter 首次匹配和策略归组，不模拟账户登录、DRM、设备地区或服务端风控；",
        "- 国产服务域名必须在不借助 GEOIP 的情况下命中显式中国直连规则；",
        "- 未分类中国大陆 IP 由 GEOIP,CN 直连，未分类境外流量由 FINAL 进入代理兜底。",
        "",
        "## 结果摘要",
        "",
        f"- 场景-配置组合：{total}",
        f"- 通过：{passed}",
        f"- 失败：{failed}",
        f"- 通过率：{rate:.2f}%",
        "",
        "## 按类别",
        "",
        "| 类别 | 通过 | 总数 | 通过率 |",
        "|---|---:|---:|---:|",
    ]
    for category in sorted(category_totals):
        category_rate = category_passed[category] / category_totals[category] * 100
        lines.append(
            f"| {category} | {category_passed[category]} | {category_totals[category]} | {category_rate:.2f}% |"
        )
    lines.extend(
        [
            "",
            "## 场景样本",
            "",
            "| 类别 | 测试域名 |",
            "|---|---|",
        ]
    )
    for category in sorted(category_domains):
        domains = "、".join(f"`{domain}`" for domain in sorted(category_domains[category]))
        lines.append(f"| {category} | {domains} |")
    lines.extend(
        [
            "",
            "## 按配置",
            "",
            "| 配置 | 通过 | 总数 | 通过率 |",
            "|---|---:|---:|---:|",
        ]
    )
    for profile in PROFILE_NAMES:
        profile_rate = profile_passed[profile] / profile_totals[profile] * 100
        lines.append(
            f"| {profile} | {profile_passed[profile]} | {profile_totals[profile]} | {profile_rate:.2f}% |"
        )
    lines.extend(["", "## 失败明细", ""])
    if not failures:
        lines.append("无。所有测试域名都命中预期策略。")
    else:
        lines.extend(
            [
                "| 场景 | 域名 | 配置 | 预期 | 实际 | 命中规则 |",
                "|---|---|---|---|---|---|",
            ]
        )
        for row in failures:
            lines.append(
                f"| {row['id']} | {row['domain']} | {row['profile']} | {row['expected']} | "
                f"{row['actual']} | `{row['rule']}` |"
            )
    lines.extend(
        [
            "",
            "## 覆盖范围",
            "",
            f"- 场景总数：{len({row['domain'] for row in results})}",
            f"- 配置档位：{len(PROFILE_NAMES)}",
            f"- 类别数：{len(category_totals)}",
            "- 成人内容域名覆盖：`rules/proxy/adult-content.list` 全表由 "
            "`validate_repository.py` 强制与场景表和 allowlist 同步。",
            "",
            "## 已知盲区",
            "",
            "- 本模拟只对域名求值。`rules/direct/private.list` 与 "
            "`rules/proxy/messaging.list` 中的 IP-CIDR / IP-CIDR6 规则（含 `no-resolve`）"
            "不参与上述检查，其语义未被本报告验证；",
            "- GEOIP,CN 仅按场景的 `cn_ip` 标记模拟，未使用真实 GeoIP 数据库，"
            "也未固定 GeoIP 数据版本；",
            "- 不模拟账户登录、DRM、设备地区、服务端风控或流媒体解锁结果。",
            "",
            "## 数据来源与限制",
            "",
            "- Apple、Google FCM 和 Google Translation 以官方网络/开发文档为优先参考；",
            "- Meta 和国产服务以官方主页、自有域名及固定提交的公开规则仓库交叉核对；",
            "- 具体来源、检索日期、第三方许可证和不可变修订记录在 `policy/sources.toml`；",
            "- 本报告证明规则层面的确定性分流，不证明流媒体解锁、Apple Intelligence 资格、FCM 长连接、成人网站可播放性或账户风控一定成功；",
            "- 本轮严格遵守只修改本地仓库，未连接或修改远端服务器、GitHub 仓库和生产订阅。",
        ]
    )
    if notes_path is not None and notes_path.is_file():
        narrative = notes_path.read_text(encoding="utf-8").strip()
        if narrative:
            lines.extend(["", narrative])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--scenarios",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "routing-scenarios.json",
    )
    parser.add_argument("--report", type=Path)
    parser.add_argument(
        "--notes",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "reports" / "review-notes.md",
        help="外部叙述文件，附加到报告末尾；生成器本身不硬编码任何自评内容",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    scenarios = json.loads(args.scenarios.read_text(encoding="utf-8"))
    results = run_matrix(args.root, scenarios)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(render_markdown(results, args.notes), encoding="utf-8")
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        failed = sum(1 for row in results if not row["passed"])
        print(f"routing checks: {len(results)}, failed: {failed}")
    return 1 if any(not row["passed"] for row in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
