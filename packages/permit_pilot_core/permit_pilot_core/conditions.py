"""Standard NYC conditions-of-approval library for clerk request-changes."""

STANDARD_CONDITIONS: list[dict[str, str]] = [
    {
        "id": "site_safety",
        "label": "Submit updated site safety plan per BC Chapter 33 before work begins.",
        "code": "BC 3301",
    },
    {
        "id": "lpc_scope",
        "label": "LPC approval letter required when work affects a landmark or historic district.",
        "code": "LPC Rule 2-01",
    },
    {
        "id": "dep_clearance",
        "label": "Resolve open DEP ECB violations or obtain DEP clearance letter.",
        "code": "DEP Rules",
    },
    {
        "id": "professional_cert",
        "label": "PW1 and professional certification must be signed by a registered design professional.",
        "code": "BC 28-104",
    },
    {
        "id": "drawings_stamp",
        "label": "Upload stamped architectural drawings matching the approved scope of work.",
        "code": "BC 28-105",
    },
    {
        "id": "insurance",
        "label": "Certificate of liability insurance naming NYC as additional insured.",
        "code": "AC 28-105.12",
    },
]


def list_conditions() -> list[dict[str, str]]:
    return list(STANDARD_CONDITIONS)
