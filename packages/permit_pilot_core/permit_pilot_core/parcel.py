from __future__ import annotations

from permit_pilot_core.models import CreateCaseRequest
from permit_pilot_core.socrata.client import SocrataClient


async def resolve_parcel(
    payload: CreateCaseRequest,
    socrata: SocrataClient | None = None,
) -> CreateCaseRequest:
    """Fill BIN / address / borough / owner from live PLUTO + building footprints.

    Shared by clerk intake and seed bootstrap so those paths cannot drift.
    """
    if payload.bin and payload.address and payload.borough and payload.owner:
        return payload
    client = socrata or SocrataClient()
    rows = await client.pluto_by_bbl(payload.bbl)
    if not rows:
        return payload
    row = rows[0]
    footprints = await client.building_footprints_by_bbl(payload.bbl, limit=1)
    bin_from_footprint = str(footprints[0].get("bin") or "") if footprints else ""
    return payload.model_copy(
        update={
            "bin": payload.bin or bin_from_footprint or str(row.get("bin") or ""),
            "address": payload.address or str(row.get("address") or ""),
            "borough": payload.borough or str(row.get("borough") or ""),
            "owner": payload.owner or str(row.get("ownername") or ""),
        }
    )
