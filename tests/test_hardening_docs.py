import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class HardeningDocumentationTest(unittest.TestCase):
    def test_agent_denies_secret_files_after_broad_read_allow(self):
        agent = (ROOT / ".opencode" / "agent" / "cycling-coach.md").read_text(
            encoding="utf-8")
        permissions = agent.partition("permission:")[2].partition("---")[0]
        self.assertLess(permissions.index('"*": allow'), permissions.index('".env": deny'))
        for pattern in ('".env": deny', '".env.*": deny',
                        '"*.env": deny', '"*.env.*": deny'):
            self.assertIn(pattern, permissions)

    def test_agent_does_not_reintroduce_historical_budget_rule(self):
        agent = (ROOT / ".opencode" / "agent" / "cycling-coach.md").read_text(
            encoding="utf-8")
        schedule = agent.partition("## Regras de agendamento")[2].partition(
            "## Workflow")[0]
        self.assertNotIn("cap_diario * 7", schedule)
        self.assertNotIn("min 0.55", schedule)

    def test_roadmap_declares_repo_ownership_without_vault_exception(self):
        roadmap = (ROOT / "docs" / "ROADMAP.md").read_text(encoding="utf-8")
        intro = roadmap.partition("## Backlog")[0]
        self.assertIn("canônico no repo", intro)
        self.assertIn("vault é somente espelho", intro)
        for forbidden in ("única exceção", "documento canônico do vault",
                          "ZoneIntegrityTest compara os dois lados"):
            self.assertNotIn(forbidden, intro)

    def test_security_recipe_does_not_pass_secret_in_grep_argv(self):
        guide = (ROOT / "docs" / "ROTEIRO-TESTES.md").read_text(encoding="utf-8")
        security = guide.partition("## 11. Segurança e boas práticas")[2].partition(
            "## 12.")[0]
        self.assertNotIn("grep -ci \"$(grep -oP", security)
        self.assertIn("capture_output=True", security)


if __name__ == "__main__":
    unittest.main()
