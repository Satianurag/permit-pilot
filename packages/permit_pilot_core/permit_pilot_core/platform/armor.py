from __future__ import annotations

from google.api_core.client_options import ClientOptions
from google.cloud import modelarmor_v1

from permit_pilot_core.settings import get_settings


class ArmorVerdict(dict):
    @property
    def blocked(self) -> bool:
        return bool(self.get("blocked"))


def _client() -> modelarmor_v1.ModelArmorClient:
    settings = get_settings()
    location = settings.model_armor_location
    return modelarmor_v1.ModelArmorClient(
        transport="rest",
        client_options=ClientOptions(api_endpoint=f"modelarmor.{location}.rep.googleapis.com"),
    )


def _template_name() -> str:
    settings = get_settings()
    return (
        f"projects/{settings.project_id}/locations/{settings.model_armor_location}"
        f"/templates/{settings.model_armor_template}"
    )


def _blocked(result) -> bool:
    match_state = getattr(result, "filter_match_state", None)
    if match_state is None:
        return False
    name = getattr(match_state, "name", str(match_state))
    return name in {"MATCH_FOUND", "2"} or int(match_state) == 2


def sanitize_user_prompt(text: str) -> ArmorVerdict:
    if not text.strip():
        return ArmorVerdict(blocked=False, text=text, findings=[])
    client = _client()
    response = client.sanitize_user_prompt(
        request=modelarmor_v1.SanitizeUserPromptRequest(
            name=_template_name(),
            user_prompt_data=modelarmor_v1.DataItem(text=text),
        )
    )
    result = response.sanitization_result
    blocked = _blocked(result)
    findings = [str(result.filter_match_state)]
    return ArmorVerdict(blocked=blocked, text=text, findings=findings, invocation=str(result.invocation_result))


def sanitize_model_response(text: str) -> ArmorVerdict:
    if not text.strip():
        return ArmorVerdict(blocked=False, text=text, findings=[])
    client = _client()
    response = client.sanitize_model_response(
        request=modelarmor_v1.SanitizeModelResponseRequest(
            name=_template_name(),
            model_response_data=modelarmor_v1.DataItem(text=text),
        )
    )
    result = response.sanitization_result
    blocked = _blocked(result)
    return ArmorVerdict(blocked=blocked, text=text, findings=[str(result.filter_match_state)])
