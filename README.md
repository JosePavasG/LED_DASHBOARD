# LED Dashboard

Control remoto de un LED con efectos PWM mediante MQTT, usando un **Seeed Studio XIAO ESP32S3** y un dashboard web en tiempo real.

## Arquitectura

```
┌──────────────┐      MQTT       ┌────────────────┐      MQTT/WS     ┌──────────────┐
│  XIAO ESP32  │◄──────────────► │   HiveMQ       │◄────────────────►│  Dashboard   │
│  MicroPython │   broker.hivemq │   (público)    │    WebSocket     │  (browser)   │
└──────────────┘      :1883      └────────────────┘      :8000       └──────────────┘
```

El microcontrolador se conecta vía WiFi al broker MQTT público de HiveMQ. El dashboard web se conecta al mismo broker por WebSocket. Ambos comparten tópicos MQTT para enviar comandos y recibir estado/telemetría en tiempo real.

## Funcionalidades

- **On / Off / Toggle** del LED
- **Efectos PWM no-bloqueantes:** breathe, blink, strobe, SOS (morse), fade in, fade out
- **Control de brillo** 0–100% con curva cuadrática para percepción natural
- **Telemetría en tiempo real:** RSSI WiFi, uptime, RAM libre, IP
- **LWT (Last Will & Testament):** detección automática de online/offline del dispositivo
- **Reconexión automática** WiFi y MQTT con watchdog (40s)
- **UI optimista** en el dashboard: respuesta visual instantánea antes de confirmación MQTT

## Estructura del proyecto

```
├── firmware/
│   ├── main.py         # Firmware MicroPython (lógica LED, WiFi, MQTT)
│   └── config.py       # Configuración WiFi, MQTT, hardware y efectos
├── web/
│   └── index.html      # Dashboard web (HTML + CSS + JS, sin dependencias de build)
├── pymakr.conf         # Configuración Pymakr para upload a la placa
└── .gitignore
```

## Hardware

- **Placa:** Seeed Studio XIAO ESP32S3
- **LED:** Pin GPIO 21 (activo bajo)
- **PWM:** 1000 Hz, 10-bit (0–1023)

## Setup

### Firmware

1. Instala [MicroPython](https://micropython.org/) en la XIAO ESP32S3
2. Edita `firmware/config.py` con tus credenciales WiFi y preferencias MQTT
3. Sube la carpeta `firmware/` a la placa con [Pymakr](https://marketplace.visualstudio.com/items?itemName=pycom.Pymakr) (VS Code) o `ampy`

### Dashboard web

Abre `web/index.html` directamente en un navegador. No requiere servidor ni build — se conecta al broker MQTT por WebSocket (`ws://broker.hivemq.com:8000/mqtt`).

## Comandos MQTT

Publicar en el tópico `xiao_pavas/led/cmd`:

| Comando            | Descripción                    |
|--------------------|--------------------------------|
| `on`               | Enciende el LED                |
| `off`              | Apaga el LED                   |
| `toggle`           | Alterna on/off                 |
| `breathe`          | Efecto respiración cíclica     |
| `blink`            | Parpadeo (1 Hz)                |
| `strobe`           | Parpadeo rápido (10 Hz)        |
| `sos`              | Patrón SOS en morse            |
| `fade_in`          | Encendido gradual              |
| `fade_out`         | Apagado gradual                |
| `brightness:0..100`| Ajustar brillo (porcentaje)    |

## Tópicos MQTT

| Tópico                          | Dirección    | Descripción                    |
|---------------------------------|--------------|--------------------------------|
| `xiao_pavas/led/cmd`           | Dashboard → Device | Comandos de control      |
| `xiao_pavas/led/status`        | Device → Dashboard | Estado JSON (retained)   |
| `xiao_pavas/device/telemetry`  | Device → Dashboard | Telemetría periódica     |
| `xiao_pavas/device/online`     | Device → Dashboard | LWT online/offline       |
