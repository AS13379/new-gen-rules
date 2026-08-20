import importlib.util
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts" / "validate_repository.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_repository", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load repository validator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class RepositoryValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = load_validator()

    def copy_repo(self) -> tuple[tempfile.TemporaryDirectory, Path]:
        temp = tempfile.TemporaryDirectory()
        target = Path(temp.name) / "repo"
        shutil.copytree(ROOT, target, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        return temp, target

    def test_current_repository_is_valid(self):
        self.assertEqual(self.validator.validate_repository(ROOT), [])

    def test_reject_list_cannot_contain_adult_content_site(self):
        temp, repo = self.copy_repo()
        self.addCleanup(temp.cleanup)
        path = repo / "rules" / "reject" / "ads-base.list"
        path.write_text(path.read_text(encoding="utf-8") + "DOMAIN-SUFFIX,pornhub.com\n", encoding="utf-8")
        errors = self.validator.validate_repository(repo)
        self.assertTrue(any("captures adult content" in error for error in errors), errors)

    def test_reject_rule_cannot_capture_adult_site_by_keyword_or_suffix(self):
        """Exact-match guarding is not enough: broader forms must also fail."""
        bypasses = [
            "DOMAIN-KEYWORD,porn",
            "DOMAIN-KEYWORD,hentai",
            "DOMAIN-SUFFIX,www.pornhub.com",
            "DOMAIN-SUFFIX,tv",
            "DOMAIN,redtube.com",
        ]
        for rule in bypasses:
            with self.subTest(rule=rule):
                temp, repo = self.copy_repo()
                self.addCleanup(temp.cleanup)
                path = repo / "rules" / "reject" / "ads-base.list"
                path.write_text(path.read_text(encoding="utf-8") + rule + "\n", encoding="utf-8")
                errors = self.validator.validate_repository(repo)
                self.assertTrue(
                    any("captures adult content" in error for error in errors),
                    f"{rule} was not blocked: {errors}",
                )

    def test_adult_allowlist_must_stay_in_sync_with_rules(self):
        temp, repo = self.copy_repo()
        self.addCleanup(temp.cleanup)
        path = repo / "rules" / "proxy" / "adult-content.list"
        path.write_text(
            path.read_text(encoding="utf-8") + "DOMAIN-SUFFIX,newly-added-adult.example\n",
            encoding="utf-8",
        )
        errors = self.validator.validate_repository(repo)
        self.assertTrue(any("adult-sites-allow.txt" in error for error in errors), errors)

    def test_reject_rule_cannot_shadow_a_mainland_direct_rule(self):
        temp, repo = self.copy_repo()
        self.addCleanup(temp.cleanup)
        path = repo / "rules" / "reject" / "ads-base.list"
        path.write_text(
            path.read_text(encoding="utf-8") + "DOMAIN-SUFFIX,ads.weibo.com\n", encoding="utf-8"
        )
        errors = self.validator.validate_repository(repo)
        self.assertTrue(any("shadows direct rule" in error for error in errors), errors)

    def test_profile_ruleset_path_cannot_escape_rules_directory(self):
        temp, repo = self.copy_repo()
        self.addCleanup(temp.cleanup)
        path = repo / "profiles" / "Mini.ini"
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "ruleset=🎯 中国直连,rules/direct/private.list",
                "ruleset=🎯 中国直连,../../../etc/hosts",
                1,
            ),
            encoding="utf-8",
        )
        errors = self.validator.validate_repository(repo)
        self.assertTrue(
            any("unsafe ruleset path" in error or "escapes rules/" in error for error in errors),
            errors,
        )

    def test_duplicate_rule_in_one_file_is_rejected(self):
        temp, repo = self.copy_repo()
        self.addCleanup(temp.cleanup)
        path = repo / "rules" / "proxy" / "crypto.list"
        path.write_text(path.read_text(encoding="utf-8") + "DOMAIN-SUFFIX,okx.com\n", encoding="utf-8")
        errors = self.validator.validate_repository(repo)
        self.assertTrue(any("duplicate rule" in error for error in errors), errors)

    def test_exact_rule_cannot_appear_in_multiple_policy_files(self):
        temp, repo = self.copy_repo()
        self.addCleanup(temp.cleanup)
        path = repo / "rules" / "proxy" / "microsoft.list"
        path.write_text(
            path.read_text(encoding="utf-8") + "DOMAIN-SUFFIX,github.com\n",
            encoding="utf-8",
        )
        errors = self.validator.validate_repository(repo)
        self.assertTrue(any("cross-file duplicate rule" in error for error in errors), errors)

    def test_stale_generated_profile_is_rejected(self):
        temp, repo = self.copy_repo()
        self.addCleanup(temp.cleanup)
        path = repo / "profiles" / "Mini.ini"
        path.write_text(path.read_text(encoding="utf-8") + "; stale\n", encoding="utf-8")
        errors = self.validator.validate_repository(repo)
        self.assertTrue(any("stale generated profile" in error for error in errors), errors)

    def test_github_actions_are_pinned_to_full_commit_shas(self):
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        for action in ["actions/checkout", "actions/setup-python"]:
            self.assertRegex(
                workflow,
                rf"uses: {re.escape(action)}@[0-9a-f]{{40}}",
                f"{action} must be pinned to an immutable commit SHA",
            )

    def test_third_party_sources_require_revision_and_license(self):
        temp, repo = self.copy_repo()
        self.addCleanup(temp.cleanup)
        path = repo / "policy" / "sources.toml"
        text = path.read_text(encoding="utf-8")
        text = text.replace(
            'revision = "4178770badecb1b349fbcd62c737e0d7a2079729"\n',
            "",
            1,
        )
        path.write_text(text, encoding="utf-8")
        errors = self.validator.validate_repository(repo)
        self.assertTrue(any("immutable revision" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
