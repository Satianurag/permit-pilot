from __future__ import annotations

from typing import Any

import httpx

from permit_pilot_core.socrata import datasets as ds

TIMEOUT = httpx.Timeout(30.0, connect=10.0)


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
