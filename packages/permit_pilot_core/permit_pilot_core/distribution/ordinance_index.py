"""Backward-compatible hint list. Canonical lookup is distribution.ordinance."""

from permit_pilot_core.distribution.ordinance import (
    ORDINANCE_HINTS as ORDINANCE_INDEX,
    citation_resolves as is_known_citation,
    citation_valid_for_department,
)

__all__ = ["ORDINANCE_INDEX", "citation_valid_for_department", "is_known_citation"]
