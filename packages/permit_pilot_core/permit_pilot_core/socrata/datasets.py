"""NYC Open Data dataset IDs — always read from Settings so they are overridable."""

from permit_pilot_core.settings import get_settings


def __getattr__(name: str) -> str:
    settings = get_settings()
    mapping = {
        "PLUTO": settings.nyc_dataset_pluto,
        "PERMITS": settings.nyc_dataset_permits,
        "FILINGS": settings.nyc_dataset_filings,
        "DOB_VIOLATIONS": settings.nyc_dataset_dob_violations,
        "DEP_ECB": settings.nyc_dataset_dep_ecb,
        "LANDMARKS": settings.nyc_dataset_landmarks,
        "FDNY_VIOLATIONS": settings.nyc_dataset_fdny_violations,
        "HPD_VIOLATIONS": settings.nyc_dataset_hpd_violations,
        "BUILDING_FOOTPRINTS": settings.nyc_dataset_building_footprints,
    }
    if name not in mapping:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return mapping[name]
