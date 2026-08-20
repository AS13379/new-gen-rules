import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIMULATOR_PATH = ROOT / "scripts" / "simulate_routing.py"
SCENARIOS_PATH = ROOT / "tests" / "fixtures" / "routing-scenarios.json"
PROFILES = ["Mini", "Mini_Adblock", "Standard", "Standard_Adblock", "Full", "Full_Adblock"]


def load_simulator():
    spec = importlib.util.spec_from_file_location("simulate_routing", SIMULATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load routing simulator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class StrictMainlandRoutingSimulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.simulator = load_simulator()
        cls.scenarios = json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))

    def expected_target(self, scenario, profile):
        tier = profile.split("_", 1)[0].lower()
        if scenario.get("ad"):
            if profile.endswith("_Adblock"):
                return "🛑 广告拦截"
            return scenario.get("non_adblock_expected", {}).get(tier, "🐟 漏网之鱼")
        return scenario["expected"][tier]

    def test_all_requested_scenarios_route_to_expected_policy(self):
        failures = []
        for scenario in self.scenarios:
            for profile in PROFILES:
                result = self.simulator.route_domain(
                    ROOT,
                    profile,
                    scenario["domain"],
                    cn_ip=scenario.get("cn_ip", False),
                )
                expected = self.expected_target(scenario, profile)
                if result.target != expected:
                    failures.append(
                        f"{scenario['id']} [{profile}]: expected {expected}, "
                        f"got {result.target} via {result.rule}"
                    )
        self.assertEqual(failures, [])

    def test_adult_content_defaults_to_a_user_controlled_group(self):
        """Adult sites must land in a selectable group, not the ad-block group.

        The default is proxied and the user can switch that group to REJECT in
        the client. What must not happen is an ad rule capturing the site and
        removing that choice.
        """
        adult = [case for case in self.scenarios if case["category"] == "成人内容"]
        self.assertTrue(adult)
        for scenario in adult:
            for profile in PROFILES:
                result = self.simulator.route_domain(ROOT, profile, scenario["domain"])
                self.assertNotEqual(
                    "🛑 广告拦截",
                    result.target,
                    f"{profile}: {scenario['domain']} was captured by the ad group "
                    f"via {result.rule}",
                )
                self.assertIn("adult-content.list", result.source, f"{profile}: {scenario['domain']}")

    def test_full_profiles_expose_reject_as_an_adult_group_option(self):
        """The user decides proxy vs block, so REJECT must be selectable."""
        for profile in ["Full", "Full_Adblock"]:
            text = (ROOT / "profiles" / f"{profile}.ini").read_text(encoding="utf-8")
            group = [
                line
                for line in text.splitlines()
                if line.startswith("custom_proxy_group=🔞 成人内容")
            ]
            self.assertEqual(len(group), 1, profile)
            self.assertIn("[]REJECT", group[0], f"{profile}: adult group must offer REJECT")

    def test_mainland_services_match_explicit_domain_rules_without_geoip(self):
        mainland_categories = {"微信生态", "国产社交", "国产视频", "国产AI"}
        for scenario in self.scenarios:
            if scenario["category"] not in mainland_categories:
                continue
            result = self.simulator.route_domain(ROOT, "Full_Adblock", scenario["domain"], cn_ip=False)
            self.assertEqual("🎯 中国直连", result.target, scenario["domain"])
            self.assertIn("china-services.list", result.source)

    def test_bilibili_has_explicit_route_per_tier(self):
        """哔哩哔哩是大陆服务，必须显式规则，不能靠 GEOIP 兜底。

        Full 档暴露独立分组（默认直连、可切代理看港澳台番），
        Standard/Mini 直接并入中国直连。
        """
        for scenario in self.scenarios:
            if scenario["category"] != "哔哩哔哩":
                continue
            for profile in PROFILES:
                result = self.simulator.route_domain(ROOT, profile, scenario["domain"], cn_ip=False)
                self.assertIn("bilibili.list", result.source, f"{profile}: {scenario['domain']}")
                expected = "📺 哔哩哔哩" if profile.startswith("Full") else "🎯 中国直连"
                self.assertEqual(expected, result.target, f"{profile}: {scenario['domain']}")

    def test_full_bilibili_group_defaults_to_direct(self):
        """哔哩哔哩组默认直连，代理仅作为可选切出的选项。"""
        for profile in ["Full", "Full_Adblock"]:
            text = (ROOT / "profiles" / f"{profile}.ini").read_text(encoding="utf-8")
            group = [
                line
                for line in text.splitlines()
                if line.startswith("custom_proxy_group=📺 哔哩哔哩")
            ]
            self.assertEqual(len(group), 1, profile)
            self.assertTrue(group[0].startswith("custom_proxy_group=📺 哔哩哔哩`select`[]DIRECT"), profile)
            self.assertIn("[]♻️ 自动选择", group[0], profile)

    def test_report_covers_every_profile_scenario_pair(self):
        results = self.simulator.run_matrix(ROOT, self.scenarios)
        self.assertEqual(len(results), len(PROFILES) * len(self.scenarios))
        self.assertTrue(all("passed" in row for row in results))

    def test_report_numbers_are_derived_from_results(self):
        """The report must state the measured totals, not a hardcoded claim."""
        results = self.simulator.run_matrix(ROOT, self.scenarios)
        report = self.simulator.render_markdown(results)
        self.assertIn(f"- 场景-配置组合：{len(results)}", report)
        self.assertIn(f"- 通过：{sum(1 for row in results if row['passed'])}", report)
        self.assertIn(f"- 失败：{sum(1 for row in results if not row['passed'])}", report)
        # Every scenario domain must appear in the rendered sample table.
        for scenario in self.scenarios:
            self.assertIn(scenario["domain"], report, scenario["id"])

    def test_report_totals_track_a_subset(self):
        """Shrinking the input must shrink the reported totals."""
        subset = self.scenarios[:3]
        results = self.simulator.run_matrix(ROOT, subset)
        report = self.simulator.render_markdown(results)
        self.assertIn(f"- 场景-配置组合：{len(PROFILES) * len(subset)}", report)
        self.assertNotIn(f"- 场景-配置组合：{len(PROFILES) * len(self.scenarios)}", report)

    def test_report_narrative_comes_from_external_notes(self):
        """Narrative text must be injected, never hardcoded in the generator."""
        results = self.simulator.run_matrix(ROOT, self.scenarios[:1])
        bare = self.simulator.render_markdown(results, None)
        self.assertNotIn("人工维护记录", bare)
        with tempfile.TemporaryDirectory() as tmp:
            notes = Path(tmp) / "notes.md"
            notes.write_text("## 人工维护记录\n\nsentinel-9f3a\n", encoding="utf-8")
            injected = self.simulator.render_markdown(results, notes)
        self.assertIn("sentinel-9f3a", injected)

    def test_report_declares_ip_rule_blind_spot(self):
        """IP-CIDR rules are never evaluated, so the report must say so."""
        results = self.simulator.run_matrix(ROOT, self.scenarios[:1])
        report = self.simulator.render_markdown(results)
        self.assertIn("## 已知盲区", report)
        self.assertIn("IP-CIDR", report)

    def test_simulator_ignores_ip_rules(self):
        """Documents the known blind spot as an executable fact."""
        self.assertFalse(self.simulator.domain_matches("IP-CIDR,10.0.0.0/8,no-resolve", "10.0.0.1"))
        self.assertFalse(self.simulator.domain_matches("IP-CIDR6,2001:b28:f23d::/48", "2001:b28:f23d::1"))

    def test_every_adult_content_rule_has_a_scenario(self):
        """The adult content rule list and the scenario table must stay in sync."""
        rule_path = ROOT / "rules" / "proxy" / "adult-content.list"
        domains = set()
        for raw in rule_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith(("#", ";")):
                continue
            parts = [part.strip() for part in line.split(",")]
            if len(parts) >= 2 and parts[0] in {"DOMAIN", "DOMAIN-SUFFIX"}:
                domains.add(parts[1].lower())
        covered = {case["domain"].lower() for case in self.scenarios}
        self.assertEqual(sorted(domains - covered), [])


if __name__ == "__main__":
    unittest.main()
