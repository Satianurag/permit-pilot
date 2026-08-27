"""Cloud Run telemetry bootstrap must not swallow exporter failures."""

from __future__ import annotations

import os
import unittest
from unittest import mock


class TelemetrySetupTest(unittest.TestCase):
    def setUp(self) -> None:
        from permit_pilot_core.observability import telemetry

        telemetry._initialized = False
        from permit_pilot_core.settings import get_settings

        get_settings.cache_clear()

    def tearDown(self) -> None:
        from permit_pilot_core.observability import telemetry

        telemetry._initialized = False
        from permit_pilot_core.settings import get_settings

        get_settings.cache_clear()

    def test_skips_when_not_on_cloud_run(self) -> None:
        from permit_pilot_core.observability.telemetry import setup_telemetry

        env = {k: v for k, v in os.environ.items() if k != "K_SERVICE"}
        with mock.patch.dict(os.environ, env, clear=True):
            setup_telemetry()

    def test_raises_when_exporter_fails_on_cloud_run(self) -> None:
        from permit_pilot_core.observability import telemetry

        telemetry._initialized = False
        with mock.patch.dict(
            os.environ,
            {"K_SERVICE": "permit-pilot", "GOOGLE_CLOUD_PROJECT": "demo-project"},
            clear=False,
        ):
            from permit_pilot_core.settings import get_settings

            get_settings.cache_clear()
            with mock.patch(
                "opentelemetry.exporter.cloud_trace.CloudTraceSpanExporter",
                side_effect=RuntimeError("exporter down"),
            ):
                from permit_pilot_core.observability.telemetry import setup_telemetry

                with self.assertRaises(RuntimeError):
                    setup_telemetry()


if __name__ == "__main__":
    unittest.main()
