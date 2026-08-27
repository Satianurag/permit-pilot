"""Observability console link builder."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services" / "api"))


class ObservabilityLinksTest(unittest.TestCase):
    def setUp(self) -> None:
        from permit_pilot_core.settings import get_settings

        get_settings.cache_clear()

    def tearDown(self) -> None:
        from permit_pilot_core.settings import get_settings

        get_settings.cache_clear()

    def test_orchestrator_traces_url_and_no_langfuse(self) -> None:
        from permit_pilot_api.config import observability_links

        env = {
            "GOOGLE_CLOUD_PROJECT": "demo-project",
            "GOOGLE_CLOUD_LOCATION": "us-central1",
            "ORCHESTRATOR_ENGINE_ID": "3804069988814290944",
            "ORCHESTRATOR_REGISTRY_AGENT_UID": "agentregistry-00000000-0000-0000-ff8f-12ba5a2edc54",
            "AGENT_GATEWAY_NAME": "permit-pilot-egress",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            from permit_pilot_core.settings import get_settings

            get_settings.cache_clear()
            links = observability_links(case_id="case-abc", project_id="demo-project")

        self.assertIn("traces/list", links["cloud_trace_url"] or "")
        self.assertIn("agentregistry-00000000-0000-0000-ff8f-12ba5a2edc54", links["agent_observability_url"] or "")
        self.assertNotIn("reasoningEngines", links["agent_observability_url"] or "")
        self.assertEqual(links["case_id"], "case-abc")
        self.assertNotIn("langfuse_url", links)
        self.assertNotIn("gcp_workflows_url", links)


if __name__ == "__main__":
    unittest.main()
