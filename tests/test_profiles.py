import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = ROOT / "scripts" / "build_profiles.py"


def load_generator():
    spec = importlib.util.spec_from_file_location("build_profiles", GENERATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load profile generator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ProfileGenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.generator = load_generator()
        cls.profiles = cls.generator.build_all(ROOT)

    def test_generates_six_public_profiles(self):
        self.assertEqual(
            set(self.profiles),
            {
                "Full",
                "Full_Adblock",
                "Standard",
                "Standard_Adblock",
                "Mini",
                "Mini_Adblock",
            },
        )

    def test_mini_matches_original_lightweight_design(self):
        for name in ["Mini", "Mini_Adblock"]:
            text = self.profiles[name]
            for group in ["🚀 节点选择", "♻️ 自动选择", "🎯 中国直连", "🐟 漏网之鱼"]:
                self.assertIn(f"custom_proxy_group={group}`", text)
            for absent in ["📢 谷歌服务", "🍎 Apple服务", "💹 加密货币", "🔞 成人内容", "📺 哔哩哔哩", "🇭🇰 香港节点"]:
                self.assertNotIn(f"custom_proxy_group={absent}`", text)

    def test_standard_is_moderately_grouped_without_region_or_exchange_groups(self):
        for name in ["Standard", "Standard_Adblock"]:
            text = self.profiles[name]
            for group in ["🚀 节点选择", "♻️ 自动选择", "📢 谷歌服务", "🍎 Apple服务", "💬 AI平台", "📲 通讯社交", "🎥 流媒体", "Ⓜ️ Microsoft服务", "🎯 中国直连", "🐟 漏网之鱼"]:
                self.assertIn(f"custom_proxy_group={group}`", text)
            for absent in ["💹 加密货币", "🔞 成人内容", "📹 YouTube", "🎮 游戏平台", "💻 开发者服务", "📺 哔哩哔哩", "🇭🇰 香港节点"]:
                self.assertNotIn(f"custom_proxy_group={absent}`", text)

    def test_full_has_detailed_business_groups_but_no_region_groups(self):
        for name in ["Full", "Full_Adblock"]:
            text = self.profiles[name]
            for group in ["📢 谷歌服务", "🍎 Apple服务", "💬 AI平台", "📲 通讯社交", "🎥 流媒体", "Ⓜ️ Microsoft服务", "📺 哔哩哔哩", "💹 加密货币", "🎮 游戏平台", "💻 开发者服务", "🔞 成人内容"]:
                self.assertIn(f"custom_proxy_group={group}`", text)
            for region in ["香港节点", "日本节点", "新加坡节点", "美国节点", "台湾节点", "韩国节点"]:
                self.assertNotIn(region, text)

    def test_all_proxy_service_groups_default_to_manual_node_selection(self):
        for name in ["Standard", "Standard_Adblock", "Full", "Full_Adblock"]:
            text = self.profiles[name]
            for group in ["📢 谷歌服务", "🍎 Apple服务", "💬 AI平台", "📲 通讯社交", "🎥 流媒体", "Ⓜ️ Microsoft服务", "🐟 漏网之鱼"]:
                line = next(line for line in text.splitlines() if line.startswith(f"custom_proxy_group={group}`"))
                self.assertIn("`select`[]🚀 节点选择`[]♻️ 自动选择`.*`[]DIRECT", line, f"{name}: {group}")

    def test_node_selection_lists_real_nodes_before_auto_selection(self):
        for name, text in self.profiles.items():
            line = next(line for line in text.splitlines() if line.startswith("custom_proxy_group=🚀 节点选择`"))
            self.assertIn("`select`.*`[]♻️ 自动选择`[]DIRECT", line, name)

    def test_other_service_groups_include_automatic_selection(self):
        for name, text in self.profiles.items():
            for line in text.splitlines():
                if not line.startswith("custom_proxy_group="):
                    continue
                group = line.split("=", 1)[1].split("`", 1)[0]
                if group in {"🎯 中国直连", "🛑 广告拦截", "🍎 Apple服务", "📺 哔哩哔哩"}:
                    continue
                if group in {"🚀 节点选择", "♻️ 自动选择"}:
                    continue
                self.assertIn("[]♻️ 自动选择", line, f"{name}: {group} lacks auto selection")

    def test_every_select_group_lists_all_nodes_directly(self):
        for name, text in self.profiles.items():
            for line in text.splitlines():
                if not line.startswith("custom_proxy_group="):
                    continue
                group = line.split("=", 1)[1].split("`", 1)[0]
                if group in {"🎯 中国直连", "🛑 广告拦截", "♻️ 自动选择"}:
                    continue
                self.assertIn("`.*", line, f"{name}: {group} 应直接列出所有节点，实际: {line}")

    def test_final_group_offers_reject_and_all_nodes(self):
        for name, text in self.profiles.items():
            line = next(l for l in text.splitlines() if l.startswith("custom_proxy_group=🐟 漏网之鱼`"))
            self.assertIn("[]REJECT", line, f"{name}: 漏网之鱼应提供 REJECT")
            self.assertIn("`select`[]🚀 节点选择`[]♻️ 自动选择`.*`[]DIRECT`[]REJECT", line, name)

    def test_all_ads_share_one_group_only_in_adblock_profiles(self):
        for name, text in self.profiles.items():
            if name.endswith("_Adblock"):
                self.assertIn("custom_proxy_group=🛑 广告拦截`select`[]REJECT`[]DIRECT", text)
                self.assertIn("rules/reject/ads-base.list", text)
                self.assertNotIn("rules/reject/adult-ads.list", text)
                self.assertNotIn("应用净化", text)
                self.assertNotIn("隐私防护", text)
            else:
                self.assertNotIn("custom_proxy_group=🛑 广告拦截`", text)
                self.assertNotIn("rules/reject/", text)

    def test_rules_prioritize_services_before_cn_geoip_and_proxy_unknowns(self):
        for name, text in self.profiles.items():
            lines = [line for line in text.splitlines() if line.startswith("ruleset=")]
            geoip = next(i for i, line in enumerate(lines) if "[]GEOIP,CN" in line)
            final = next(i for i, line in enumerate(lines) if "[]FINAL" in line)
            self.assertLess(geoip, final)
            self.assertIn("🐟 漏网之鱼,[]FINAL", lines[final])
            for rule_file in ["google.list", "apple.list", "meta.list", "messaging.list", "crypto.list", "bilibili.list"]:
                idx = next(i for i, line in enumerate(lines) if f"rules/proxy/{rule_file}" in line)
                self.assertLess(idx, geoip)
            self.assertNotIn("ChinaDomain", text)
            self.assertNotIn("GoogleCN", text)
            self.assertNotIn("UnBan", text)

    def test_full_routes_crypto_and_adult_content_to_dedicated_groups(self):
        for name in ["Full", "Full_Adblock"]:
            text = self.profiles[name]
            self.assertIn("ruleset=💹 加密货币,rules/proxy/crypto.list", text)
            self.assertIn("ruleset=🔞 成人内容,rules/proxy/adult-content.list", text)
            self.assertIn("ruleset=📺 哔哩哔哩,rules/proxy/bilibili.list", text)
        for name in ["Mini", "Mini_Adblock", "Standard", "Standard_Adblock"]:
            text = self.profiles[name]
            self.assertIn("ruleset=🚀 节点选择,rules/proxy/crypto.list", text)
            self.assertIn("ruleset=🚀 节点选择,rules/proxy/adult-content.list", text)
            self.assertIn("ruleset=🎯 中国直连,rules/proxy/bilibili.list", text)

    def test_initial_rule_content_matches_requirements(self):
        google = (ROOT / "rules" / "proxy" / "google.list").read_text(encoding="utf-8")
        apple = (ROOT / "rules" / "proxy" / "apple.list").read_text(encoding="utf-8")
        crypto = (ROOT / "rules" / "proxy" / "crypto.list").read_text(encoding="utf-8")
        ad_block = (ROOT / "rules" / "reject" / "ads-base.list").read_text(encoding="utf-8")
        adult_content = (ROOT / "rules" / "proxy" / "adult-content.list").read_text(encoding="utf-8")
        adult_allow = (ROOT / "tests" / "fixtures" / "adult-sites-allow.txt").read_text(encoding="utf-8")

        for expected in ["translate.google.com", "translate.googleapis.com", "fcm.googleapis.com", "mtalk.google.com", "alt8-mtalk.google.com"]:
            self.assertIn(expected, google)
        for expected in ["icloud.com", "icloud-content.com", "apple-relay.apple.com", "apple-relay.cloudflare.com"]:
            self.assertIn(expected, apple)
        self.assertIn("okx.com", crypto)
        for site in [line.strip() for line in adult_allow.splitlines() if line.strip() and not line.startswith("#")]:
            self.assertIn(site, adult_content)
            self.assertNotIn(site, ad_block)

    def test_specialized_rules_are_not_shadowed_by_broader_service_lists(self):
        google = (ROOT / "rules" / "proxy" / "google.list").read_text(encoding="utf-8")
        youtube = (ROOT / "rules" / "proxy" / "youtube.list").read_text(encoding="utf-8")
        microsoft = (ROOT / "rules" / "proxy" / "microsoft.list").read_text(encoding="utf-8")
        developer = (ROOT / "rules" / "proxy" / "developer.list").read_text(encoding="utf-8")

        self.assertNotIn("DOMAIN-SUFFIX,googlevideo.com", google)
        self.assertIn("DOMAIN-SUFFIX,googlevideo.com", youtube)
        self.assertNotIn("DOMAIN-SUFFIX,github.com", microsoft)
        self.assertNotIn("DOMAIN-SUFFIX,githubusercontent.com", microsoft)
        self.assertIn("DOMAIN-SUFFIX,github.com", developer)
        self.assertIn("DOMAIN-SUFFIX,githubusercontent.com", developer)


if __name__ == "__main__":
    unittest.main()
