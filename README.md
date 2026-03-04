# IoT Control Center

Dashboard web profesional para control remoto de un LED con efectos PWM mediante MQTT, usando un **Seeed Studio XIAO ESP32S3** y un broker Mosquitto self-hosted con Docker.

## Arquitectura

```
┌──────────────┐     MQTT:1883     ┌────────────────┐     WebSocket:9001    ┌──────────────┐
│  XIAO ESP32  │◄────────────────►│   Mosquitto    │◄──────────────────►│  Dashboard   │
│  MicroPython │                   │   (Docker)     │   nginx proxy /mqtt  │  (browser)   │
└──────────────┘                   └────────────────┘                      └──────────────┘
                                         │
                                   docker-compose
                                   ┌─────┴─────┐
                                   │  nginx    │  :80  →  Dashboard + WS proxy
                                   └───────────┘
```

El microcontrolador se conecta vía WiFi al broker Mosquitto local (puerto 1883). El dashboard web se sirve con nginx y se conecta al broker por WebSocket a través del proxy nginx (`/mqtt` → Mosquitto :9001). Todo corre en Docker Compose.

## Funcionalidades

### Device Control
- **On / Off** del LED con badge de estado animado en el efecto activo
- **Efectos PWM no-bloqueantes:** breathe, blink, strobe, SOS (morse), fade in, fade out
- **Control de brillo** 0–100% con curva cuadrática para percepción natural

### Telemetry Dashboard
- **Gauges circulares SVG** para RAM libre, Flash usado y temperatura del MCU
- **Stat cards** para WiFi RSSI (con barra de señal), uptime e IP
- **Exportar a CSV** con un click

### Event Logs
- Log en tiempo real con badges de tipo (OK / ERR / INFO)
- **Filtros** por tipo de evento
- **Auto-scroll** configurable
- **Exportar a CSV**

### UI/UX
- **Sidebar colapsable** con navegación por pestañas (Control / Telemetry / Logs)
- **Tema dark/light** con transiciones suaves
- **Breadcrumbs** en cada página
- **Animaciones** de entrada, hover y transición en toda la interfaz
- **Diseño responsive** (desktop + mobile con sidebar overlay)
- **UI optimista:** respuesta visual instantánea antes de confirmación MQTT
- **LWT (Last Will & Testament):** detección automática de online/offline del dispositivo
- **Reconexión automática** WiFi y MQTT con watchdog (40s)

## Estructura del proyecto

```
├── firmware/
│   ├── main.py              # Firmware MicroPython (lógica LED, WiFi, MQTT)
│   └── config.py            # Configuración WiFi, MQTT, hardware y efectos
├── web/
│   └── index.html           # Dashboard web (HTML + CSS + JS, single-file)
├── mosquitto/
│   └── config/
│       └── mosquitto.conf   # Configuración del broker Mosquitto
├── nginx/
│   └── default.conf         # Nginx: sirve dashboard + proxy WebSocket
├── docker-compose.yml       # Mosquitto + Nginx en Docker
├── pymakr.conf              # Configuración Pymakr para upload a la placa
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
2. Edita `firmware/config.py` con tus credenciales WiFi y la IP del broker
3. Sube la carpeta `firmware/` a la placa con [Pymakr](https://marketplace.visualstudio.com/items?itemName=pycom.Pymakr) (VS Code) o `ampy`

## Comandos MQTT

Publicar en el tópico `xiao_pavas/led/cmd`:

| Comando             | Descripción                    |
|---------------------|--------------------------------|
| `on`                | Enciende el LED                |
| `off`               | Apaga el LED                   |
| `toggle`            | Alterna on/off                 |
| `breathe`           | Efecto respiración cíclica     |
| `blink`             | Parpadeo (1 Hz)                |
| `strobe`            | Parpadeo rápido (10 Hz)        |
| `sos`               | Patrón SOS en morse            |
| `fade_in`           | Encendido gradual              |
| `fade_out`          | Apagado gradual                |
| `brightness:0..100` | Ajustar brillo (porcentaje)    |

## Tópicos MQTT

| Tópico                         | Dirección          | Descripción                |
|---------------------------------|--------------------|----------------------------|
| `xiao_pavas/led/cmd`           | Dashboard → Device | Comandos de control        |
| `xiao_pavas/led/status`        | Device → Dashboard | Estado JSON (retained)     |
| `xiao_pavas/device/telemetry`  | Device → Dashboard | Telemetría periódica       |
| `xiao_pavas/device/online`     | Device → Dashboard | LWT online/offline         |
