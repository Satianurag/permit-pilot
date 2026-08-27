"""Phase 0 config: Settings has no project-ID fallbacks and exposes platform constants."""

from __future__ import annotations

import os
import unittest
from unittest import mock

from pydantic import ValidationError


class SettingsContractTest(unittest.TestCase):
    def setUp(self) -> None:
        from permit_pilot_core.settings import get_settings

        get_settings.cache_clear()

    def tearDown(self) -> None:
        from permit_pilot_core.settings import get_settings

        get_settings.cache_clear()

    def test_missing_project_is_an_error(self) -> None:
        from permit_pilot_core.settings import Settings

        env = {k: v for k, v in os.environ.items() if k != "GOOGLE_CLOUD_PROJECT"}
        with mock.patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ValidationError):
                Settings()  # type: ignore[call-arg]

    def test_vertex_defaults_and_dataset_ids(self) -> None:
        from permit_pilot_core.settings import Settings, get_settings
        from permit_pilot_core.socrata import datasets as ds

        with mock.patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test-project"}, clear=False):
            get_settings.cache_clear()
            settings = Settings()  # type: ignore[call-arg]
            self.assertEqual(settings.project_id, "test-project")
            self.assertEqual(settings.vertex_location, "global")
            self.assertEqual(settings.vertex_model, "gemini-3.5-flash")
            self.assertEqual(settings.nyc_dataset_dep_ecb, "skr7-cxt3")
            self.assertEqual(ds.DEP_ECB, "skr7-cxt3")
            self.assertEqual(ds.PLUTO, "64uk-42ks")

    def test_google_cloud_region_alias(self) -> None:
        from permit_pilot_core.settings import Settings, get_settings

        with mock.patch.dict(
            os.environ,
            {"GOOGLE_CLOUD_PROJECT": "test-project", "GOOGLE_CLOUD_REGION": "europe-west1"},
            clear=False,
        ):
            os.environ.pop("GOOGLE_CLOUD_LOCATION", None)
            get_settings.cache_clear()
            settings = Settings()  # type: ignore[call-arg]
            self.assertEqual(settings.region, "europe-west1")


if __name__ == "__main__":
    unittest.main()
