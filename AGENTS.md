# Repository instructions

## Scope

This repository contains the source of the Home Assistant `llm_local_intents`
integration. It is a provider-neutral contributor to Home Assistant's LLM
platform. The supported baseline is Home Assistant Core `2026.8.0+`.

The separate Home Assistant configuration repository is outside this
workspace's implementation scope. Do not edit
`C:\Users\klonw\PhpstormProjects\home-assistant`, its `custom_components`
dist directory, package files, or prompt files from this repository. Record
configuration-repository work in
`docs/home-assistant-config-handoff.md` for the next agent instead.

## Integration contract

- Preserve the domain and YAML key `llm_local_intents`.
- Metadata is supplied by Home Assistant's merged YAML configuration; the
  integration must not read package files directly or add a file watcher.
- Expose one stable `local_assist_...` tool per validated intent.
- Support both custom `intent_script` handlers and registered built-in Assist
  handlers through the direct intent API.
- Keep native Home Assistant tools available. Never retry a failed local intent
  through a native tool and never invoke Conversation API recursively.
- Generic policy text may be localized (currently `ru` and `en`), but source
  code must not contain room names, entity IDs, hardware assumptions, or
  examples from one user's installation.
- Invalid metadata entries should be isolated and logged; a successful reload
  replaces the immutable catalog atomically, while a failed reload preserves the
  previous snapshot.
- Avoid exposing secrets, user phrases, tokens, or complete slot values in
  ordinary logs.

## Source layout

- `catalog.py` — pure metadata parsing, validation, descriptors, and sorting.
- `schema.py` — tool parameter schemas and dependency-free test fallback.
- `intent_adapter.py` — Home Assistant intent registry and direct execution.
- `llm_tools.py` — dynamic per-intent LLM tool instances.
- `prompt.py` — generic language-selected policy fragments.
- `__init__.py` — YAML setup, catalog state, and reload handling.
- `llm.py` — Home Assistant LLM platform hook.
- `tests/` — isolated tests using Home Assistant API stubs.

Keep pure validation independent from Home Assistant imports where practical;
keep HA-version-specific behavior in the adapter/setup layer.

## Configuration metadata

The supported shape is:

```yaml
llm_local_intents:
  intents:
    ExampleIntent:
      description: "Short action description"
      examples:
        - "natural phrase"
      priority: 50
      slots: {}
```

`description` and at least one non-empty example are required. `expose` defaults
to `true`; `priority` defaults to `50`. Slot types are `integer`, `number`,
`string`, and `boolean`, with optional requiredness, bounds, and enum mapping.

## Verification

Run these commands from the repository root before reporting implementation
completion:

```bash
python -m compileall -q custom_components/llm_local_intents
python -m pytest tests
```

Also run `git diff --check`. HACS/Hassfest validation is provided by CI when
available. Real HA configuration-check, reload, Assist Debug, and LLM
acceptance checks are external follow-up work described in the handoff.

For executable-source or test changes, inspect the complete diff and complete
the repository's required independent review workflow before declaring the
work finished. Preserve unrelated user changes, including pre-existing file
deletions.
