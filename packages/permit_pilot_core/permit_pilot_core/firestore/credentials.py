from __future__ import annotations

import os
import subprocess

from google.auth.exceptions import DefaultCredentialsError
from google.cloud import firestore
from google.oauth2.credentials import Credentials


def _gcloud_access_token() -> str:
    return subprocess.check_output(
        ["gcloud", "auth", "print-access-token"],
        text=True,
        stderr=subprocess.DEVNULL,
    ).strip()


def _running_on_cloud_run() -> bool:
    return bool(os.environ.get("K_SERVICE"))


def firestore_client(project_id: str | None = None) -> firestore.Client:
    project = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT", "gen-lang-client-0233250350")
    try:
        return firestore.Client(project=project)
    except DefaultCredentialsError:
        if _running_on_cloud_run():
            raise RuntimeError(
                "Firestore requires the Cloud Run service account (ADC). "
                "Attach roles/datastore.user to the runtime service account."
            ) from None
        token = _gcloud_access_token()
        creds = Credentials(token=token)
        return firestore.Client(project=project, credentials=creds)
