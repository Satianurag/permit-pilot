"""Agent Runtime wrapper that pins gemini-3.5-flash to the global Vertex location."""

from __future__ import annotations

import os

try:
    from agentplatform.agent_engines import AdkApp
except ImportError:  # pragma: no cover - vertexai package name on some runtimes
    from vertexai.agent_engines import AdkApp

from google.adk.agents import Agent
from google.adk.apps import App


def _force_global_vertex() -> None:
    os.environ["VERTEX_LOCATION"] = "global"
    os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "true")


class FleetAdkApp(AdkApp):
    """AdkApp that keeps gemini-3.5-flash on global after Agent Runtime injects us-central1."""

    def set_up(self):
        _force_global_vertex()
        super().set_up()
        _force_global_vertex()


def wrap_for_runtime(agent: Agent) -> FleetAdkApp:
    return FleetAdkApp(
        app=App(name=agent.name, root_agent=agent),
        enable_tracing=True,
    )
