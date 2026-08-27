from __future__ import annotations

import unittest

from permit_pilot_core.platform.identity import agent_iap_principal, agent_spiffe


class IdentityTest(unittest.TestCase):
    def test_proj_trust_domain(self) -> None:
        spiffe = agent_spiffe(
            "501242612091453440",
            project_number="538666547847",
            location="us-central1",
        )
        self.assertTrue(spiffe.startswith("agents.global.proj-538666547847.system.id.goog/"))
        self.assertNotIn("project-538666547847", spiffe)
        self.assertIn("reasoningEngines/501242612091453440", spiffe)
        principal = agent_iap_principal(
            "501242612091453440",
            project_number="538666547847",
            location="us-central1",
        )
        self.assertTrue(principal.startswith("principal://agents.global.proj-"))

    def test_empty_without_project_number(self) -> None:
        self.assertEqual(agent_spiffe("123", project_number=""), "")
