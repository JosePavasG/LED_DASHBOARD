# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

IoT LED Control Dashboard — a full-stack project for controlling LEDs on ESP32 devices via MQTT. Includes MicroPython firmware, a single-file web dashboard, and Docker infrastructure (Mosquitto + Nginx).

## Architecture

- **Multi-device**: Each device uses MAC-based MQTT topics (`d/{MAC}/...`)
- **Single-file dashboard**: `web/index.html` (HTML + CSS + JS, ~90KB)
- **Remote config**: Dashboard sends settings via MQTT, firmware persists to `/config.json`
- **WiFi recovery**: If WiFi fails, firmware deletes `config.json` and restarts with `config.py` defaults

## Key Files

### Firmware (MicroPython)
- `firmware/boot.py` — FW_VERSION, config_store.load(), boot_log.init()
- `firmware/main.py` — Main loop: WiFi, MQTT, LED effects, telemetry, web server
- `firmware/config.example.py` — Config template (copy to `config.py`, which is gitignored)
- `firmware/lib/config_store.py` — Runtime config with JSON persistence and MQTT validation
- `firmware/lib/boot_log.py` — Boot counter and crash log (NVS)
- `firmware/lib/morse.py` — Non-blocking Morse code encoder
- `firmware/lib/webserver.py` — Minimal HTTP server (serves dashboard from device)

### Dashboard
- `web/index.html` — Single-file dashboard with i18n (EN/ES), dark/light theme, multi-device selector

### Infrastructure
- `docker-compose.yml` — Mosquitto broker (1883/9001) + Nginx (80)
- `mosquitto/config/` — Broker configuration
- `nginx/` — Reverse proxy configuration

## Conventions

- Firmware prints use English prefixes (`[MQTT]`, `[Boot]`, `[Config]`) with Spanish or English messages
- Dashboard i18n uses `data-i18n` attributes and `_i18n_data` dictionary (EN/ES)
- Config keys in `config_store.py` use snake_case; config.py attributes use UPPER_SNAKE_CASE
- MQTT topics: `d/{MAC-hyphenated}/led/cmd`, `d/{MAC}/device/telemetry`, etc.
- `config.py` is gitignored — never commit credentials
