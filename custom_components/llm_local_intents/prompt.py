"""Generic, project-independent policy fragments for local Assist tools."""

from __future__ import annotations

from collections.abc import Mapping


POLICY_PROMPTS: Mapping[str, str] = {
    "ru": (
        "Сначала проверь доступные локальные Assist-инструменты. "
        "Если запрос соответствует локальному инструменту, обязательно вызови его. "
        "Не заменяй локальный инструмент универсальным native-инструментом по "
        "area/domain. Native-инструмент используй только если подходящего локального "
        "инструмента нет и действие однозначно. Если локальный инструмент вернул "
        "ошибку, сообщи об ошибке и не повторяй действие через другой инструмент. "
        "Если несколько локальных инструментов одинаково подходят, задай один "
        "короткий уточняющий вопрос."
    ),
    "en": (
        "Check the available local Assist tools first. If the request matches a "
        "local tool, call it. Do not replace a local tool with a broad native "
        "area/domain tool. Use a native tool only when no local tool matches and "
        "the requested action is unambiguous. If a local tool returns an error, "
        "report the error and do not retry the action through another tool. If "
        "multiple local tools are equally plausible, ask one short clarification "
        "question."
    ),
}


def normalize_language(language: str | None) -> str:
    """Map an HA language tag to the supported policy language."""
    if not language:
        return "en"
    normalized = language.lower().replace("_", "-").split("-", 1)[0]
    return normalized if normalized in POLICY_PROMPTS else "en"


def policy_for_language(language: str | None) -> str:
    """Return the generic policy for an LLM request language."""
    return POLICY_PROMPTS[normalize_language(language)]
