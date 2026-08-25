from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from permit_pilot_core.socrata.client import SocrataClient, borough_label
from permit_pilot_api.auth import get_current_user

router = APIRouter(prefix="/nyc", tags=["nyc"], dependencies=[Depends(get_current_user)])


def _normalize_bbl(raw: str) -> str:
    digits = "".join(ch for ch in raw if ch.isdigit())
    if "." in raw:
        digits = raw.split(".", 1)[0]
        digits = "".join(ch for ch in digits if ch.isdigit())
    return digits[:10]


@router.get("/resolve-address")
async def resolve_address(
    address: Annotated[str, Query(min_length=3)],
    borough: Annotated[str, Query(min_length=1)],
):
    client = SocrataClient()
    street = address.strip().upper()
    rows = await client.pluto_by_address(borough=borough.strip(), street=street)
    matches = []
    for row in rows:
        bbl = _normalize_bbl(str(row.get("bbl") or ""))
        if len(bbl) != 10:
            continue
        footprints = await client.building_footprints_by_bbl(bbl, limit=1)
        bin_ = str(footprints[0].get("bin") or "") if footprints else ""
        matches.append(
            {
                "address": str(row.get("address") or address),
                "bbl": bbl,
                "bin": bin_,
                "borough": borough_label(str(row.get("borough") or borough)),
                "owner": str(row.get("ownername") or ""),
                "zoning_district": str(row.get("zonedist1") or row.get("zonedist") or ""),
            }
        )
    if not matches:
        raise HTTPException(status_code=404, detail="No PLUTO match for that address and borough")
    return {"matches": matches}
