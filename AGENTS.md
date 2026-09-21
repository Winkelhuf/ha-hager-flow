# AI Agent Instructions

This repository contains the Home Assistant custom integration `hager_flow` for Hager flow Modbus systems.

This is a real custom integration project intended for Home Assistant and HACS publication. It is not a template or starter blueprint.

The purpose of this file is to keep development consistent with Home Assistant custom integration standards, reduce avoidable mistakes, and support maintainable publishing.

## Project identity

- Domain: `hager_flow`
- Title: `Hager flow Modbus`
- Class prefix: `HagerFlow`
- Repository: `Winkelhuf/ha-hager-flow`

## Product scope

This integration connects to a local Hager flow Energy Management System over Modbus TCP and exposes the relevant device data and controls in Home Assistant.

The integration may include:

- main system monitoring
- power meter entities
- Witty wallbox entities
- SG Ready status and data
- supporting diagnostics and configuration

## Repository structure

Important repository parts:

- `custom_components/hager_flow/` — integration source code
- `config/` — local Home Assistant config for development/testing
- `tests/` — automated tests
- `.github/` — GitHub workflows and issue templates
- `README.md` — user documentation and installation steps
- `hacs.json` — HACS metadata
- `manifest.json` — Home Assistant integration metadata
- `LICENSE` — repository license

## Required architecture

Keep the integration aligned with Home Assistant custom integration patterns.

### Core rules

- Entities should read from the coordinator, not directly from the device API.
- Device logic should be separated from entity/UI presentation.
- Config flow logic belongs in the config flow layer.
- Service actions should be registered in `async_setup()`.
- Use async I/O and clear type hints.
- Keep files small and focused.
- Avoid unnecessary abstraction layers.

### Package layout

Use the project structure consistently:

- `api/` — API client and exceptions
- `coordinator/` — data coordinator logic
- `config_flow_handler/` — config flow, options and validators
- `entity/` — base entity classes
- `entity_utils/` — helper logic for entities
- `<platform>/` — sensor, switch, etc.
- `service_actions/` — service actions
- `utils/` — cross-cutting utilities

Do not add new top-level packages such as `common/`, `shared/`, `lib/`, or `helpers/` unless there is a clear need.

## Coding standards

- Python 4 spaces, double quotes, 120 column limit
- type hints required
- async for I/O operations
- stable unique IDs for entities and devices
- translation keys and entity descriptions preferred over hardcoded names
- avoid template or placeholder leftovers in the codebase
- keep comments minimal and only for meaningful exceptions or workarounds

## Validation before publishing

Before publishing or merging a change:

- run the repository validation tooling that exists in the repo
- ensure HACS metadata is valid
- ensure `manifest.json` is valid
- verify README installation instructions still match actual behavior
- run relevant tests for changed behavior
- keep the repo in a maintainable, clean state

The repository currently uses GitHub Actions-based validation in:

- `.github/workflows/lint.yml`
- `.github/workflows/validate.yml`

Do not rely on missing helper scripts or template-only tooling. Only use commands and scripts that are actually present in the repository.

## Development workflow

Use the repository’s actual tooling and Home Assistant testing setup, not blueprint-era helper scripts.

Keep this in mind:

- use the local config directory for testing
- validate integration behavior with Home Assistant-aware tooling
- avoid reading runtime state from `.storage` unless it is a deliberate debug step and the result is understood
- keep testing and validation reproducible

## Publishing requirements

Before publishing to HACS or making the repo public:

- check `hacs.json`
- check `manifest.json`
- confirm the README accurately describes installation and setup
- ensure all user-facing strings and config flows are correct
- ensure the project is understandable to a future maintainer
- remove stale template or bootstrap content
- keep brand assets, metadata, and documentation current

## Contribution expectations

- Small, focused changes are preferred
- Add tests for behavior changes when practical
- Avoid unrelated refactors in the same patch
- Respect Home Assistant conventions
- Prefer compatibility and clarity over cleverness
- Keep the integration publishable and maintainable

## Quick checklist

Before finishing a task, confirm:

- the code fits the project structure
- Home Assistant patterns are followed
- validation was run with the repo’s real tooling
- the README still
