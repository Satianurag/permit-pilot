from __future__ import annotations

import unittest

from permit_pilot_core.models import CreateCaseRequest
from permit_pilot_core.parcel import resolve_parcel


class FakeSocrata:
    def __init__(self, rows: list[dict], footprints: list[dict]) -> None:
        self.rows = rows
        self.footprints = footprints

    async def pluto_by_bbl(self, bbl: str, limit: int = 5) -> list[dict]:
        return self.rows

    async def building_footprints_by_bbl(self, bbl: str, limit: int = 1) -> list[dict]:
        return self.footprints


class ResolveParcelTest(unittest.IsolatedAsyncioTestCase):
    async def test_fills_bin_from_footprint_when_pluto_bin_empty(self) -> None:
        payload = CreateCaseRequest(
            address="",
            bbl="3014930048",
            bin="",
            work_type="Alteration",
            owner="",
            borough="",
        )
        socrata = FakeSocrata(
            rows=[{"bin": "", "address": "761 MACON STREET", "borough": "BK", "ownername": "OWNER"}],
            footprints=[{"bin": "3040031"}],
        )
        resolved = await resolve_parcel(payload, socrata)
        self.assertEqual(resolved.bin, "3040031")
        self.assertEqual(resolved.address, "761 MACON STREET")
        self.assertEqual(resolved.owner, "OWNER")

    async def test_keeps_existing_bin(self) -> None:
        payload = CreateCaseRequest(
            address="761 MACON STREET",
            bbl="3014930048",
            bin="3040031",
            work_type="Alteration",
            owner="OWNER",
            borough="BROOKLYN",
        )
        socrata = FakeSocrata(rows=[{"bin": "999"}], footprints=[{"bin": "888"}])
        resolved = await resolve_parcel(payload, socrata)
        self.assertEqual(resolved.bin, "3040031")


if __name__ == "__main__":
    unittest.main()
