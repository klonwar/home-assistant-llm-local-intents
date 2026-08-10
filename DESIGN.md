# LLM Local Intents — initial integration design

## Understanding summary

- The copied `LLM Reminders` repository will become a new Home Assistant
  integration named **LLM Local Intents**.
- Reminder-specific behavior is explicitly out of scope for this first step:
  no reminder manager, persistence, scheduling, satellite announcements,
  reminder tools, prompts, translations, or config flow will remain.
- The first version is a minimally loadable integration with an LLM platform
  entry point that currently exposes no tools.
- The integration domain is `llm_local_intents` and the repository URL is
  `https://github.com/klonwar/home-assistant-llm-local-intents`.
- HACS and Hassfest validation workflows remain enabled, as does Release
  Please for future Conventional Commit-based releases.
- The existing brand icon is retained for later replacement.

## Assumptions

- The initial version is reset to `0.1.0`.
- The integration is local-only, has no external dependencies, and performs
  no network requests.
- No config entries, entities, or YAML configuration are needed yet.
- No migration or compatibility layer for `llm_reminders` is required.
- `LICENSE`, `.gitignore`, `.gitattributes`, and the existing GitHub workflow
  structure are retained and updated only where names or paths require it.

## Final design

```text
custom_components/llm_local_intents/
├── __init__.py
├── const.py
├── llm.py
├── llm_tools.py
├── manifest.json
└── brand/
    └── icon.png
```

- `const.py` defines `DOMAIN = "llm_local_intents"`.
- `__init__.py` exposes a minimal `async_setup` that returns `True`.
- `llm_tools.py` exposes `build_tools()` and returns an empty list as the
  extension point for future local-intent tools.
- `llm.py` implements Home Assistant's `async_get_tools(...)`. It returns
  `None` while `build_tools()` is empty; future tools can be returned through
  `llm.LLMTools` without changing the platform entry point.
- `manifest.json` uses the new domain/name and repository URLs, sets
  `config_flow` to `false`, and starts at version `0.1.0`.

The repository keeps HACS/Hassfest validation and Release Please workflows,
updates HACS and Release Please metadata to the new integration path, and
rewrites the README and changelog for this clean starting point. Reminder
modules, prompts, translations, old tests, stale references, and generated
artifacts are removed.

## Behavior and verification

- `async_setup(...)` returns `True` without registering runtime state.
- `async_get_tools(...)` returns `None` deterministically while no tools are
  defined.
- Tests cover package structure, metadata/version alignment, empty tool
  registry, minimal setup behavior, and absence of the old domain.
- Deterministic checks are:

  ```text
  python -m compileall -q custom_components/llm_local_intents
  python -m pytest tests
  ```

## Decision log

1. **Create a clean new domain instead of preserving reminder behavior.**
   Compatibility aliases and a reminder migration were rejected because the
   goal is a new integration, not an upgrade path for `llm_reminders`.
2. **Use `llm_local_intents` / `LLM Local Intents` as the identity.**
   This matches the new repository purpose and requested GitHub URL.
3. **Keep a minimal `llm.py` that returns no tools.**
   Omitting the platform would remove the intended extension point; returning
   `None` avoids advertising non-existent tools.
4. **Keep `const.py` and `llm_tools.py` as functional extension points.**
   A domain constant and an empty tool factory provide structure without
   retaining obsolete reminder modules or empty placeholder files.
5. **Retain HACS/Hassfest and Release Please automation.**
   These workflows are useful immediately for validation and future releases,
   while the old reminder changelog/history is reset.
6. **Retain the existing icon.**
   It is intentionally temporary and will be replaced later by the owner.
