"""IAP egressor policy for the fleet: per-agent CEL on MCP tools.

Agent Registry RuntimeIdentity uses the orgless trust domain
``agents.global.proj-{PROJECT_NUMBER}.system.id.goog`` (not ``project-``).
IAM rejects the docs-style ``project-`` prefix as an unknown member type.
"""

from __future__ import annotations

from permit_pilot_core.platform.fleet import FLEET, FleetAgent


def tool_condition(agent: FleetAgent) -> dict[str, str]:
    quoted = ", ".join(f'"{name}"' for name in agent.tools)
    return {
        "title": f"{agent.name}-tools",
        "description": f"Allow {agent.name} only its catalog MCP tools",
        "expression": (
            "api.getAttribute('iap.googleapis.com/mcp.toolName', '') "
            f"in [{quoted}]"
        ),
    }


def mcp_egressor_bindings(
    *,
    principals: dict[str, str],
    extra_members: list[str] | None = None,
) -> list[dict]:
    """Build roles/iap.egressor bindings for the Permit Tools MCP server."""
    bindings: list[dict] = []
    extras = [member for member in (extra_members or []) if member]
    if extras:
        bindings.append({"role": "roles/iap.egressor", "members": extras})
    for spec in FLEET:
        principal = principals.get(spec.name)
        if not principal:
            raise ValueError(f"missing IAP principal for {spec.name}")
        bindings.append(
            {
                "role": "roles/iap.egressor",
                "members": [principal],
                "condition": tool_condition(spec),
            }
        )
    return bindings


def endpoint_egressor_bindings(*, principals: dict[str, str]) -> list[dict]:
    """Socrata endpoint access for agents that query NYC Open Data tools."""
    members: list[str] = []
    for spec in FLEET:
        if "validate_citations" in spec.tools and set(spec.tools) <= {
            "validate_citations",
            "persist_review",
        }:
            continue
        principal = principals.get(spec.name)
        if not principal:
            raise ValueError(f"missing IAP principal for {spec.name}")
        members.append(principal)
    return [{"role": "roles/iap.egressor", "members": members}]
