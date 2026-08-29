from __future__ import annotations

from typing import Any

import httpx

from permit_pilot_core.settings import get_settings
from permit_pilot_core.socrata import datasets as ds


def _timeout() -> httpx.Timeout:
    seconds = get_settings().socrata_timeout_seconds
    return httpx.Timeout(seconds, connect=min(10.0, seconds))

BOROUGH_TO_CODE: dict[str, str] = {
    "MANHATTAN": "MN",
    "BRONX": "BX",
    "BROOKLYN": "BK",
    "QUEENS": "QN",
    "STATEN ISLAND": "SI",
}

BOROUGH_FROM_CODE: dict[str, str] = {code: name.title() for name, code in BOROUGH_TO_CODE.items()}
BOROUGH_FROM_CODE["STATEN ISLAND"] = "Staten Island"


def split_bbl(bbl: str) -> tuple[str, str, str] | None:
    """Return (borough, unpadded block, unpadded lot) from a 10-digit BBL."""
    digits = "".join(ch for ch in bbl if ch.isdigit())
    if len(digits) != 10:
        return None
    return digits[0], str(int(digits[1:6])), str(int(digits[6:10]))


def borough_code(name: str) -> str:
    normalized = name.strip().upper()
    if normalized in BOROUGH_TO_CODE:
        return BOROUGH_TO_CODE[normalized]
    if len(normalized) == 2:
        return normalized
    raise ValueError(f"Unknown NYC borough: {name}")


def borough_label(code: str) -> str:
    return BOROUGH_FROM_CODE.get(code.strip().upper(), code)


class SocrataClient:
    def __init__(self, base_url: str | None = None) -> None:
        self._base = (base_url or get_settings().nyc_open_data_base).rstrip("/")

    async def _get(self, dataset_id: str, params: dict[str, str]) -> list[dict[str, Any]]:
        url = f"{self._base}/{dataset_id}.json"
        async with httpx.AsyncClient(timeout=_timeout()) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, list):
                return []
            return data

    async def pluto_by_bbl(self, bbl: str, limit: int = 5) -> list[dict[str, Any]]:
        return await self._get(ds.PLUTO, {"$where": f"bbl='{bbl}'", "$limit": str(limit)})

    async def pluto_by_address(self, *, borough: str, street: str, limit: int = 8) -> list[dict[str, Any]]:
        borough_code_value = borough_code(borough).replace("'", "''")
        street_escaped = street.strip().upper().replace("'", "''")
        where = (
            f"upper(address) like '%{street_escaped}%' "
            f"and borough='{borough_code_value}'"
        )
        return await self._get(ds.PLUTO, {"$where": where, "$limit": str(limit)})

    async def building_footprints_by_bbl(self, bbl: str, limit: int = 5) -> list[dict[str, Any]]:
        return await self._get(
            ds.BUILDING_FOOTPRINTS,
            {"$where": f"mappluto_bbl='{bbl}'", "$limit": str(limit)},
        )

    async def permits_by_bbl(self, bbl: str, limit: int = 50) -> list[dict[str, Any]]:
        return await self._get(ds.PERMITS, {"$where": f"bbl='{bbl}'", "$limit": str(limit)})

    async def permits_by_bin(self, bin_: str, limit: int = 50) -> list[dict[str, Any]]:
        return await self._get(ds.PERMITS, {"$where": f"bin='{bin_}'", "$limit": str(limit)})

    async def filings_by_bin(self, bin_: str, limit: int = 25) -> list[dict[str, Any]]:
        return await self._get(ds.FILINGS, {"$where": f"bin='{bin_}'", "$limit": str(limit)})

    async def dob_violations_by_bin(self, bin_: str, limit: int = 100) -> list[dict[str, Any]]:
        return await self._get(
            ds.DOB_VIOLATIONS,
            {"$where": f"bin='{bin_}'", "$limit": str(limit)},
        )

    async def dob_safety_violations(self, *, bin_: str = "", bbl: str = "", limit: int = 100) -> list[dict[str, Any]]:
        if bin_:
            return await self._get(ds.DOB_SAFETY, {"$where": f"bin='{bin_}'", "$limit": str(limit)})
        if bbl:
            return await self._get(ds.DOB_SAFETY, {"$where": f"bbl='{bbl}'", "$limit": str(limit)})
        return []

    async def hpd_violations_by_bbl(self, bbl: str, limit: int = 50) -> list[dict[str, Any]]:
        parts = split_bbl(bbl)
        if not parts:
            return []
        boro, block, lot = parts
        where = f"boroid='{boro}' AND block='{block}' AND lot='{lot}'"
        return await self._get(ds.HPD_VIOLATIONS, {"$where": where, "$limit": str(limit)})

    async def landmarks_by_bbl(self, bbl: str, limit: int = 10) -> list[dict[str, Any]]:
        return await self._get(ds.LANDMARKS, {"$where": f"bbl='{bbl}'", "$limit": str(limit)})

    async def fdny_violations_by_bin(self, bin_: str, limit: int = 50) -> list[dict[str, Any]]:
        return await self._get(
            ds.FDNY_VIOLATIONS,
            {"$where": f"bin='{bin_}'", "$limit": str(limit)},
        )

    async def hpd_violations_by_bin(self, bin_: str, limit: int = 50) -> list[dict[str, Any]]:
        return await self._get(
            ds.HPD_VIOLATIONS,
            {"$where": f"bin='{bin_}'", "$limit": str(limit)},
        )

    async def dep_ecb_by_address(
        self,
        *,
        house: str,
        borough: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        borough_upper = borough.upper().replace("'", "''")
        house_escaped = house.replace("'", "''")
        where = (
            f"starts_with(violation_location_house,'{house_escaped}') "
            f"AND upper(violation_location_borough)='{borough_upper}'"
        )
        return await self._get(ds.DEP_ECB, {"$where": where, "$limit": str(limit)})
