# LLM Local Intents for Home Assistant

LLM tools for local Home Assistant Assist intents. The integration reads
metadata from the merged Home Assistant YAML configuration and exposes one
strictly-bound LLM tool per published intent.

Supported baseline: Home Assistant Core `2026.8.0+`.

## Installation

### HACS

This repository is structured as a HACS integration repository. In HACS, add
the GitHub repository as a custom repository with type **Integration**, install
it, and restart Home Assistant. See the [HACS custom repository
documentation](https://hacs.xyz/docs/faq/custom_repositories/) for details.

### Manual

Copy the integration directory into the Home Assistant configuration directory:

```text
config/
└── custom_components/
    └── llm_local_intents/
```

Restart Home Assistant after copying the files. The integration does not expose
tools until matching `llm_local_intents` metadata is present in Home Assistant's
configuration.

## Current status

- YAML metadata is validated at setup/reload and invalid entries are skipped
  without removing unrelated valid tools.
- Tools call the exact registered Assist intent directly; they do not invoke
  the Conversation API recursively and never perform a native-tool fallback.
- Generic tool-selection policy is available in Russian and English. The
  language is selected from the current LLM context, with English as fallback.
- Tools are provider-neutral and work through Home Assistant's LLM platform;
  no particular model or vendor is hard-coded.
- There is no config flow, entity, or UI configuration.

## Configuration

Add metadata beside the existing `intent_script` in a Home Assistant package.
The configuration repository is intentionally not modified by this project.

```yaml
llm_local_intents:
  intents:
    ExampleIntent:
      description: "Short description of the local action"
      examples:
        - "natural example phrase"
      priority: 50
      slots: {}
```

`description` and at least one `examples` item are required. `expose` defaults
to `true`; `priority` defaults to `50`. Slot entries support `integer`,
`number`, `string`, and `boolean` types, with optional `required`, numeric
`minimum`/`maximum`, and `enum` constraints. An enum mapping can translate a
model-facing value to the internal handler value.

The generated tool name is stable: `local_assist_` followed by the intent name
converted to snake case. The corresponding Assist handler must already be
registered by Home Assistant.

The integration validates the merged configuration supplied by Home Assistant;
it does not read package files itself. A malformed entry is skipped and logged,
while valid entries remain available. A local tool error is returned to the LLM
as an error and is never retried through a native Home Assistant tool.

After changing package metadata, use Home Assistant's normal YAML configuration
check and reload. The reload path obtains fresh merged configuration through
Home Assistant's reload helper; no file watcher is required.

After implementing or changing package metadata, follow
[`docs/home-assistant-config-handoff.md`](docs/home-assistant-config-handoff.md)
for the configuration validation, reload, and real Assist acceptance steps.

The validated architecture and decision log are in
[`docs/llm-local-intents-design.md`](docs/llm-local-intents-design.md).

The integration source intentionally contains no room names, entity IDs,
hardware assumptions, or examples from a particular Home Assistant instance.
Those belong in the configuration repository and its handoff.

## Development

Run these checks before publishing changes:

```bash
python -m compileall -q custom_components/llm_local_intents
python -m pytest tests
```

The GitHub workflows also run HACS and Hassfest validation. Real Home Assistant
reload and LLM acceptance tests are documented in the configuration handoff and
must be run in the target HA instance. Release Please creates releases from
Conventional Commits merged into `main`.
