from __future__ import annotations

from typing import Any

import httpx

from permit_pilot_core.socrata import datasets as ds

TIMEOUT = httpx.Timeout(30.0, connect=10.0)

BOROUGH_TO_CODE: dict[str, str] = {
    "MANHATTAN": "MN",
    "BRONX": "BX",
    "BROOKLYN": "BK",
    "QUEENS": "QN",
    "STATEN ISLAND": "SI",
}

BOROUGH_FROM_CODE: dict[str, str] = {code: name.title() for name, code in BOROUGH_TO_CODE.items()}
BOROUGH_FROM_CODE["STATEN ISLAND"] = "Staten Island"


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
    def __init__(self, base_url: str = ds.NYC_OPEN_DATA_BASE) -> None:
        self._base = base_url.rstrip("/")

    async def _get(self, dataset_id: str, params: dict[str, str]) -> list[dict[str, Any]]:
        url = f"{self._base}/{dataset_id}.json"
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
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
