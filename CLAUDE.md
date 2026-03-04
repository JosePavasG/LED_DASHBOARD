# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

A Claude Code configuration repository containing custom agent definitions and slash commands. There is no application source code, build system, or test suite — only `.claude/` configuration files.

## Key Files

- `.claude/agents/embedded-systems.md` — Agent (Sonnet) for firmware/microcontroller development (RTOS, bare-metal, power management, ARM Cortex-M/ESP32/STM32/nRF/AVR/RISC-V)
- `.claude/commands/code-review.md` — Slash command for code quality and security review
- `.claude/commands/refactor-code.md` — Slash command for incremental refactoring with test verification
- `.claude/commands/init-project.md` — Slash command for project scaffolding
- `.claude/commands/cleanup-cache.md` — Slash command for system cache cleanup (conservative/aggressive/maximum modes)

## Editing Conventions

Agent and command files use YAML front matter (`name`, `description`, `tools`, `model`) followed by markdown prompt content.
