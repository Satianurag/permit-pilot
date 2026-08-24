from __future__ import annotations

import json
import os

from google.cloud.workflows import executions_v1


def gcp_workflows_enabled() -> bool:
    return bool(os.environ.get("GCP_WORKFLOW_NAME"))


def start_distribution_workflow(*, case_id: str, api_base: str) -> str:
    project = os.environ["GOOGLE_CLOUD_PROJECT"]
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    name = os.environ["GCP_WORKFLOW_NAME"]
    parent = f"projects/{project}/locations/{location}/workflows/{name}"

    client = executions_v1.ExecutionsClient()
    execution = client.create_execution(
        request={
            "parent": parent,
            "execution": {
                "argument": json.dumps({"case_id": case_id, "api_base": api_base.rstrip("/")}),
            },
        }
    )
    return execution.name.rsplit("/", 1)[-1]
