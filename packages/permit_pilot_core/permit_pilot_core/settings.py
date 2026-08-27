from __future__ import annotations

import os
from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. Required values have no hardcoded project fallbacks."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    google_cloud_project: str = Field(alias="GOOGLE_CLOUD_PROJECT")
    google_cloud_project_number: str = Field(default="", alias="GOOGLE_CLOUD_PROJECT_NUMBER")
    google_cloud_location: str = Field(
        default="us-central1",
        validation_alias=AliasChoices("GOOGLE_CLOUD_LOCATION", "GOOGLE_CLOUD_REGION"),
    )
    vertex_location: str = Field(default="global", alias="VERTEX_LOCATION")
    vertex_model: str = Field(default="gemini-3.5-flash", alias="VERTEX_MODEL")

    permit_pilot_url: str = Field(default="", alias="PERMIT_PILOT_URL")
    cors_origins: str = Field(default="", alias="CORS_ORIGINS")
    mcp_tools_url: str = Field(default="", alias="MCP_TOOLS_URL")

    auth_secret_key: str = Field(default="", alias="AUTH_SECRET_KEY")
    auth_token_expire_minutes: int = Field(default=480, alias="AUTH_TOKEN_EXPIRE_MINUTES")
    clerk_bootstrap_username: str = Field(default="", alias="CLERK_BOOTSTRAP_USERNAME")
    clerk_bootstrap_password: str = Field(default="", alias="CLERK_BOOTSTRAP_PASSWORD")
    clerk_bootstrap_full_name: str = Field(default="", alias="CLERK_BOOTSTRAP_FULL_NAME")
    clerk_bootstrap_role: str = Field(default="clerk", alias="CLERK_BOOTSTRAP_ROLE")
    clerk_users_json: str = Field(default="", alias="CLERK_USERS")

    nyc_open_data_base: str = Field(
        default="https://data.cityofnewyork.us/resource",
        alias="NYC_OPEN_DATA_BASE",
    )
    citation_source_url: str = Field(
        default="https://github.com/BetaNYC/nyc-charter-laws-rules",
        alias="CITATION_SOURCE_URL",
    )
    nyc_dataset_pluto: str = Field(default="64uk-42ks", alias="NYC_DATASET_PLUTO")
    nyc_dataset_permits: str = Field(default="rbx6-tga4", alias="NYC_DATASET_PERMITS")
    nyc_dataset_filings: str = Field(default="w9ak-ipjd", alias="NYC_DATASET_FILINGS")
    nyc_dataset_dob_violations: str = Field(default="3h2n-5cm9", alias="NYC_DATASET_DOB_VIOLATIONS")
    nyc_dataset_dep_ecb: str = Field(default="skr7-cxt3", alias="NYC_DATASET_DEP_ECB")
    nyc_dataset_landmarks: str = Field(default="gpmc-yuvp", alias="NYC_DATASET_LANDMARKS")
    nyc_dataset_fdny_violations: str = Field(default="bi53-yph3", alias="NYC_DATASET_FDNY_VIOLATIONS")
    nyc_dataset_hpd_violations: str = Field(default="wvxf-dwi5", alias="NYC_DATASET_HPD_VIOLATIONS")
    nyc_dataset_building_footprints: str = Field(default="5zhs-2jue", alias="NYC_DATASET_BUILDING_FOOTPRINTS")

    review_window_days: int = Field(default=5, alias="REVIEW_WINDOW_DAYS")
    context_cache_ttl_seconds: int = Field(default=3600, alias="CONTEXT_CACHE_TTL_SECONDS")
    distribution_stale_hours: int = Field(default=24, alias="DISTRIBUTION_STALE_HOURS")
    socrata_timeout_seconds: float = Field(default=30.0, alias="SOCRATA_TIMEOUT_SECONDS")
    override_note_min_chars: int = Field(default=20, alias="OVERRIDE_NOTE_MIN_CHARS")
    login_window_seconds: int = Field(default=900, alias="LOGIN_WINDOW_SECONDS")
    login_max_failures: int = Field(default=10, alias="LOGIN_MAX_FAILURES")
    seed_on_startup: bool = Field(default=False, alias="SEED_ON_STARTUP")

    cloud_tasks_queue: str = Field(default="permit-pilot-distribution", alias="CLOUD_TASKS_QUEUE")
    cloud_tasks_location: str = Field(default="us-central1", alias="CLOUD_TASKS_LOCATION")
    cloud_tasks_service_account: str = Field(default="", alias="CLOUD_TASKS_SERVICE_ACCOUNT")

    staging_bucket: str = Field(default="", alias="AGENT_STAGING_BUCKET")
    agent_gateway_name: str = Field(default="permit-pilot-egress", alias="AGENT_GATEWAY_NAME")
    model_armor_template: str = Field(default="permit-pilot-armor", alias="MODEL_ARMOR_TEMPLATE")
    model_armor_location: str = Field(default="us-central1", alias="MODEL_ARMOR_LOCATION")
    orchestrator_engine_id: str = Field(default="", alias="ORCHESTRATOR_ENGINE_ID")
    agent_engine_ids: str = Field(default="", alias="AGENT_ENGINE_IDS")

    @property
    def project_id(self) -> str:
        return self.google_cloud_project

    @property
    def region(self) -> str:
        return self.google_cloud_location

    @property
    def project_number(self) -> str:
        if self.google_cloud_project_number:
            return self.google_cloud_project_number
        return os.environ.get("GOOGLE_CLOUD_PROJECT_NUMBER", "")

    @property
    def cors_origin_list(self) -> list[str]:
        raw = self.cors_origins or self.permit_pilot_url
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    @property
    def engine_id_map(self) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for part in self.agent_engine_ids.split(","):
            if "=" in part:
                name, engine_id = part.split("=", 1)
                mapping[name.strip()] = engine_id.strip()
        if self.orchestrator_engine_id:
            mapping.setdefault("permit_orchestrator", self.orchestrator_engine_id)
        return mapping

    @property
    def running_on_cloud_run(self) -> bool:
        return bool(os.environ.get("K_SERVICE"))

    @property
    def staging_bucket_uri(self) -> str:
        if self.staging_bucket:
            return self.staging_bucket if self.staging_bucket.startswith("gs://") else f"gs://{self.staging_bucket}"
        number = self.project_number
        if not number:
            raise RuntimeError("GOOGLE_CLOUD_PROJECT_NUMBER or AGENT_STAGING_BUCKET is required")
        return f"gs://permit-pilot-agent-staging-{number}"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


def require_project() -> str:
    return get_settings().project_id
