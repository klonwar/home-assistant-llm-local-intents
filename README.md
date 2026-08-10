# LLM Local Intents for Home Assistant

An initial skeleton for local LLM tools and intents in Home Assistant.

The first version is intentionally minimal: the integration loads through the
Home Assistant LLM platform, but it does not expose any tools yet. Future local
intents can be added through `llm_tools.py` without changing the integration
domain or repository layout.

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

Restart Home Assistant after copying the files.

## Current status

- No LLM tools are exposed yet.
- There is no config flow, entity, or UI configuration.
- The retained icon is temporary and will be replaced in a later change.

## Development

Run these checks before publishing changes:

```bash
python -m compileall -q custom_components/llm_local_intents
python -m pytest tests
```

The GitHub workflows also run HACS and Hassfest validation. Release Please
creates releases from Conventional Commits merged into `main`.
