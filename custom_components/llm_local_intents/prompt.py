"""Generic, project-independent policy fragments for local Assist tools."""

from __future__ import annotations

from collections.abc import Mapping


POLICY_PROMPTS: Mapping[str, str] = {
    "ru": (
        "<local_assist_tools_policy>\n"
        "Эти правила относятся только к локальным Assist-инструментам этой "
        "интеграции.\n\n"
        "Если запрос соответствует локальному инструменту, немедленно вызови "
        "ровно один подходящий локальный инструмент.\n"
        "Вызови его через структурированный tool-call, не заменяй вызов "
        "reasoning-текстом или обычным ответом.\n"
        "Не вызывай native tool для того же действия.\n"
        "Если подходят несколько локальных инструментов, задай один короткий "
        "вопрос с финальным `?` и не вызывай инструмент.\n"
        "Если локальный инструмент завершился ошибкой, сообщи об ошибке и не "
        "повторяй действие через native tool.\n"
        "Если локальный инструмент вернул непустой `speech`, используй его в "
        "коротком ответе.\n"
        "Если локальный инструмент не подходит, эти правила не ограничивают "
        "выбор native tools.\n"
        "</local_assist_tools_policy>"
    ),
    "en": (
        "<local_assist_tools_policy>\n"
        "These rules apply only to local Assist tools exposed by this "
        "integration.\n\n"
        "If the request matches a local tool, immediately call exactly one "
        "matching local tool.\n"
        "Use the structured tool interface; do not replace the call with "
        "reasoning or ordinary text.\n"
        "Do not call a native tool for the same action.\n"
        "If multiple local tools match, ask one concise question ending with `?` "
        "and do not call a tool.\n"
        "If a local tool fails, report the error and do not retry through a "
        "native tool.\n"
        "If the local tool returns non-empty `speech`, use it in the short "
        "response.\n"
        "If no local tool matches, these rules do not restrict native tool "
        "selection.\n"
        "</local_assist_tools_policy>"
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
