# AI Agent Instructions

This repository contains the Home Assistant custom integration `hager_flow` for Hager flow Modbus systems.

This is not a template repository and not a blueprint. It is a real custom integration intended for Home Assistant and HACS publication.

The goal of this file is to provide project-specific context for AI coding agents working in this repository so that changes stay consistent with the integration architecture and Home Assistant conventions.

## Project identity

- Domain: `hager_flow`
- Title: `Hager flow Modbus`
- Class prefix: `HagerFlow`
- Repository: `Winkelhuf/ha-hager-flow`

## Project overview

This integration connects to a local Hager flow Energy Management System over Modbus TCP and exposes relevant devices, values, and controls in Home Assistant.

It supports local discovery and monitoring of components such as:

- the main EMC system
- power meters
- Witty wallboxes
- SG Ready devices
- battery, PV, and grid-related values

The implementation follows standard Home Assistant custom integration patterns and uses the coordinator model for data flow.

## Repository structure

Key directories and files:

- `custom_components/hager_flow/` — integration source code
- `config/` — local Home Assistant configuration used for testing
- `tests/` — automated tests
- `.github/` — GitHub configuration, issue templates, and workflows
- `README.md` — user-facing project documentation
- `hacs.json` — HACS metadata for publication
- `manifest.json` — Home Assistant integration manifest
- `LICENSE` — project license

## Architecture and file rules

Keep the Home Assistant integration structure consistent with the project conventions.

### Package organization

Use this structure when adding or modifying code:

- `api/` — API client and exceptions when needed
- `coordinator/` — update coordinator logic
- `config_flow_handler/` — config flow, options, validators, schemas
- `entity/` — base entity classes and helpers
- `entity_utils/` — entity helper logic
- `<platform>/` — platform modules such as sensor or switch
- `service_actions/` — service action implementations
- `utils/` — integration-wide utilities

Top-level modules are limited to the standard integration entry points, such as:

- `config_flow.py`
- `diagnostics.py`
- `repairs.py`
- `trigger.py` / `condition.py` when applicable

Do not create new top-level packages like `common/`, `shared/`, `lib/`, or `helpers/` without a clear reason. Prefer `utils/` or `entity_utils/` instead.

### Design constraints

- Entities read from the coordinator, not directly from device APIs.
- Register service actions in `async_setup()`, not `async_setup_entry()`.
- Keep files focused and reasonably small.
- Prefer clear separation between:
  - device/data access
  - coordination
  - entity representation
  - config flow and options
- Use type hints and async I/O consistently.
- Follow standard Home Assistant custom integration patterns.
- Avoid unnecessary custom abstractions that do not add value.

## Coding standards

### Python

- 4-space indentation
- line length: 120
- double quotes
- full type hints
- async usage for I/O operations
- prefer explicit readability over cleverness

### Home Assistant conventions

- `coordinator.data` is the source for entities
- maintain stable unique IDs
- keep translation keys and `EntityDescription` metadata explicit
- avoid hardcoded display names where the architecture expects translation keys and descriptions
- do not add new device-automation files unless there is a strong, explicit need
- keep user-visible naming consistent with the integration’s supported devices and local Modbus model

### Comments and documentation

- comments should be rare and only used for non-obvious constraints, workarounds, or issue references
- larger explanations belong in `docs/development/` or in a docstring, not in inline comments
- keep repository docs focused on this project’s actual behavior, not on template boilerplate

## Validation and workflow

Use the project’s standard validation workflows and tools rather than creating ad-hoc checks.

The repository currently relies on GitHub Actions for automated validation, especially:

- `.github/workflows/lint.yml`
- `.github/workflows/validate.yml`

These cover linting, Home Assistant validation, and HACS validation.

When local validation is needed, use the repository’s actual available tooling and keep command usage consistent with the project environment. Do not assume convenience scripts exist unless they are present in the repository root.

## Local development and testing

The project is intended to be developed in a Home Assistant-aware local environment.

Use the repo’s real configuration and validation setup when available. For local testing:

- keep a clean Home Assistant test configuration under `config/`
- test changes against the real integration structure
- use the repo’s actual local tooling if present
- avoid reading runtime state directly from `.storage` unless explicitly required for debugging and it is understood to be stale

Do not assume live runtime data can be read directly from storage files. Use the Home Assistant project runtime and the repository tooling instead.

## Release and publication

This repository is intended for publication as a Home Assistant custom integration via HACS.

Keep these project files maintained and accurate:

- `README.md` — installation, configuration, features, limitations
- `hacs.json` — HACS metadata
- `manifest.json` — Home Assistant integration metadata
- `LICENSE` — legal license information
- `.github/workflows/*.yml` — CI validation and release automation

When making changes that affect users, pay attention to:

- config flow behavior
- entity IDs and unique IDs
- state values and units
- service call signatures
- compatibility of installation and setup

If a change will affect existing users, document the risk clearly and prefer a migration path where appropriate.

## GitHub and project hygiene

- Keep `README.md` accurate and project-specific
- Keep issue templates, contributing docs, and workflows up to date
- Remove stale template or placeholder content if it remains
- Keep the repository organized so it remains understandable, maintainable, and publishable
- Prefer clean, minimal repository state over leftovers from scaffold or starter templates

## Contribution expectations

- Prefer focused changes that address one clear issue or feature
- Add tests for behavioral changes where meaningful
- Validate with the repository’s actual tools before considering work complete
- Avoid unrelated refactors or broad cleanup in the same change
- When editing integration behavior, think in terms of Home Assistant runtime assumptions and user-visible impact

## Quick checklist before finishing work

Before considering a task complete:

- Does the code fit the project structure?
- Are Home Assistant patterns followed?
- Are the relevant validation workflows or local tools run?
- Is the README or docs still accurate?
- Are there any leftover blueprint/template artifacts?
- Does the change remain compatible with HACS publication?
- Is the repo still clean and understandable for future maintenance?

This repository is a real custom integration project, and all work should be aligned with that goal.