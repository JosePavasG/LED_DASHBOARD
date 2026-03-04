# IoT Control Center

> Last updated: 2026-03-04

Dashboard web profesional para control remoto de LEDs con efectos PWM mediante MQTT, soportando **N dispositivos ESP32** identificados por MAC. Usa **Seeed Studio XIAO ESP32S3** y un broker Mosquitto self-hosted con Docker.

## Arquitectura

```
┌──────────────┐                        ┌────────────────┐                       ┌──────────────┐
│  XIAO ESP32  │◄──── MQTT:1883 ──────► │   Mosquitto    │◄── WebSocket:9001 ──► │  Dashboard   │
│  MicroPython │  d/{MAC}/led/cmd ...   │   (Docker)     │   nginx proxy /mqtt   │  (browser)   │
└──────────────┘                        └────────────────┘                       └──────────────┘
       ×N                                      │
                                         docker-compose
                                         ┌─────┴─────┐
                                         │  nginx    │  :80 → Dashboard + WS proxy
                                         └───────────┘
```

Cada dispositivo se identifica por su MAC address (`AA-BB-CC-DD-EE-FF`). El dashboard descubre dispositivos automáticamente via suscripciones wildcard (`d/+/...`).

## Funcionalidades

### Multi-Device
- **Auto-discovery** de dispositivos vía MQTT wildcards
- **Device picker** con búsqueda por nombre o MAC, indicadores online/offline
- **Badge de conteo** de dispositivos online en el sidebar
- **Nombre personalizado** configurable desde Settings (persiste en el dispositivo)
- Todas las pestañas muestran datos del dispositivo seleccionado

### Device Control
- **On / Off** del LED con badge de estado animado en el efecto activo
- **Efectos PWM no-bloqueantes:** breathe, blink, strobe, SOS, fade in, fade out
- **Transmisor Morse:** envío de texto libre como código morse por el LED
- **Control de brillo** 0–100% con curva cuadrática para percepción natural

### Telemetry Dashboard
- **Gauges circulares SVG** para RAM libre, Flash usado y temperatura del MCU
- **Stat cards** para WiFi RSSI (con barra de señal), uptime, IP, MAC y versión de firmware
- **Exportar a CSV** con un click (incluye nombre de dispositivo en el archivo)

### Event Logs
- Log en tiempo real con badges de tipo (OK / ERR / INFO)
- **Filtros** por tipo de evento
- **Auto-scroll** configurable
- **Exportar a CSV** por dispositivo

### Remote Settings
- **Configuración remota** vía MQTT: WiFi, broker, timings de efectos, nombre del dispositivo
- **Escaneo WiFi** desde el dashboard (dropdown con redes, señal, auto-fill de contraseñas guardadas)
- **Validación y ACK** del dispositivo con feedback visual (success/error/restarting)
- **Persistencia** en JSON en el filesystem del ESP32

### UI/UX
- **Sidebar colapsable** con navegación por pestañas (Control / Telemetry / Logs / Settings)
- **Tema dark/light** con transiciones suaves
- **Idioma EN/ES** con toggle en el sidebar
- **Info-tips** (tooltips `?`) en todos los controles con descripción contextual
- **Diseño responsive** (desktop + mobile con sidebar overlay)
- **UI optimista:** respuesta visual instantánea antes de confirmación MQTT
- **LWT (Last Will & Testament):** detección automática de online/offline
- **Reconexión automática** WiFi y MQTT con watchdog (40s)

## Firmware pre-compilado

En `.bin/firmware.bin` se incluye una imagen binaria lista para flashear en cualquier **Seeed XIAO ESP32S3** sin necesidad de copiar archivos individuales. Contiene el firmware MicroPython completo (v1.0.0) con todos los módulos del proyecto ya integrados.

```bash
# Flashear con esptool (dirección 0x0, flash completa de 8 MB)
esptool.py --chip esp32s3 --port COM3 write_flash 0x0 .bin/firmware.bin
```

> **Nota:** Después de flashear, aún necesitas crear `config.py` con tus credenciales WiFi y MQTT (ver sección Setup → Firmware).

## Estructura del proyecto

```
├── .bin/
│   └── firmware.bin          # Imagen binaria pre-compilada para XIAO ESP32S3
├── firmware/
│   ├── boot.py                # Boot temprano + FW_VERSION (editar aquí para releases)
│   ├── main.py                # Firmware principal (WiFi, MQTT, LED, telemetría)
│   ├── config.example.py      # Template de configuración (copiar a config.py)
│   └── lib/
│       ├── config_store.py    # Config runtime con persistencia JSON + validación
│       ├── boot_log.py        # Boot counter + crash log vía NVS
│       ├── morse.py           # Generador morse no-bloqueante (ITU timing)
│       └── webserver.py       # HTTP server no-bloqueante para servir dashboard
├── web/
│   └── index.html             # Dashboard web (HTML + CSS + JS, single-file)
├── mosquitto/
│   └── config/
│       └── mosquitto.conf     # Configuración del broker Mosquitto
├── nginx/
│   └── default.conf           # Nginx: sirve dashboard + proxy WebSocket
├── docker-compose.yml         # Mosquitto + Nginx en Docker
└── .gitignore
```

## Hardware

- **Placa:** Seeed Studio XIAO ESP32S3
- **LED:** Pin GPIO 21 (activo bajo)
- **PWM:** 1000 Hz, 10-bit (0–1023)

## Setup

### Docker (broker + dashboard)

```bash
docker compose up -d
```

Esto levanta:
- **Mosquitto** en puertos 1883 (MQTT) y 9001 (WebSocket)
- **Nginx** en puerto 80 sirviendo el dashboard y haciendo proxy de WebSocket

Accede al dashboard en `http://localhost`.

### Firmware

1. Instala [MicroPython](https://micropython.org/) en la XIAO ESP32S3
2. Copia `firmware/config.example.py` a `firmware/config.py` y edita tus credenciales
3. Sube los archivos a la placa:

```bash
# Con mpremote
mpremote cp firmware/boot.py :boot.py
mpremote cp firmware/main.py :main.py
mpremote cp firmware/config.py :config.py
mpremote mkdir :lib
mpremote cp firmware/lib/config_store.py :lib/config_store.py
mpremote cp firmware/lib/boot_log.py :lib/boot_log.py
mpremote cp firmware/lib/morse.py :lib/morse.py
mpremote cp firmware/lib/webserver.py :lib/webserver.py
```

4. Copia `web/index.html` al filesystem del ESP32 si quieres servir el dashboard desde el dispositivo:

```bash
mpremote mkdir :web
mpremote cp web/index.html :web/index.html
```

## Tópicos MQTT

Cada dispositivo publica/suscribe bajo el prefijo `d/{MAC}/` donde MAC es `AA-BB-CC-DD-EE-FF` (hyphenated).

| Tópico                          | Dirección          | Descripción                       |
|---------------------------------|--------------------|-----------------------------------|
| `d/{MAC}/led/cmd`               | Dashboard → Device | Comandos de control               |
| `d/{MAC}/led/status`            | Device → Dashboard | Estado JSON (retained)            |
| `d/{MAC}/device/telemetry`      | Device → Dashboard | Telemetría periódica              |
| `d/{MAC}/device/online`         | Device → Dashboard | LWT online/offline (retained)     |
| `d/{MAC}/config/set`            | Dashboard → Device | Enviar nueva configuración        |
| `d/{MAC}/config/current`        | Device → Dashboard | Config actual (retained)          |
| `d/{MAC}/config/ack`            | Device → Dashboard | ACK de config (success/errors)    |
| `d/{MAC}/wifi/scan`             | Dashboard → Device | Solicitar escaneo WiFi            |
| `d/{MAC}/wifi/scan_results`     | Device → Dashboard | Resultados del escaneo            |

El dashboard suscribe con wildcards: `d/+/led/status`, `d/+/device/telemetry`, etc.

## Comandos MQTT

Publicar en `d/{MAC}/led/cmd`:

| Comando              | Descripción                    |
|----------------------|--------------------------------|
| `on`                 | Enciende el LED                |
| `off`                | Apaga el LED                   |
| `toggle`             | Alterna on/off                 |
| `breathe`            | Efecto respiración cíclica     |
| `blink`              | Parpadeo (1 Hz)                |
| `strobe`             | Parpadeo rápido (10 Hz)        |
| `sos`                | Patrón SOS en morse            |
| `fade_in`            | Encendido gradual              |
| `fade_out`           | Apagado gradual                |
| `brightness:0..100`  | Ajustar brillo (porcentaje)    |
| `morse:TEXTO`        | Transmitir texto en morse      |
