<p align="center">
  <h1 align="center">IoT Control Center</h1>
  <p align="center">
    Dashboard web profesional para control remoto de LEDs con efectos PWM mediante MQTT
    <br />
    Soporta <strong>N dispositivos ESP32</strong> identificados por MAC
    <br /><br />
    <a href="https://github.com/JosePavasG/LED_DASHBOARD/releases/latest"><img src="https://img.shields.io/github/v/release/JosePavasG/LED_DASHBOARD?style=for-the-badge&color=6366f1&label=Release" alt="Release"></a>
    &nbsp;
    <a href="https://github.com/JosePavasG/LED_DASHBOARD/releases/latest/download/XIAO_ESP32S3_Compilado.bin"><img src="https://img.shields.io/badge/Download-Firmware.bin-34d399?style=for-the-badge&logo=espressif&logoColor=white" alt="Download"></a>
  </p>
</p>

---

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

---

## Funcionalidades

<table>
<tr><td>

### Multi-Device
- **Auto-discovery** vía MQTT wildcards
- **Device picker** con búsqueda, indicadores online/offline
- **Nombre personalizado** (persiste en el dispositivo)
- Todas las pestañas por dispositivo seleccionado

</td><td>

### Device Control
- **On / Off** con badge animado por efecto
- **Efectos PWM:** breathe, blink, strobe, SOS, fade
- **Transmisor Morse** de texto libre
- **Brillo** 0–100% con curva cuadrática

</td></tr>
<tr><td>

### Telemetry
- **Gauges SVG** para RAM, Flash y temperatura
- **Stat cards:** RSSI, uptime, IP, MAC, firmware
- **Exportar a CSV** por dispositivo

</td><td>

### Remote Settings
- Config remota vía MQTT (WiFi, broker, timings)
- **Escaneo WiFi** con auto-fill de contraseñas
- **Olvidar redes WiFi** (browser + dispositivo)
- Validación + ACK con feedback visual

</td></tr>
<tr><td>

### WiFi Recovery
- WiFi falla → borra `config.json` → reinicia
- Siguiente boot usa `config.py` (credenciales originales)
- Permite mover dispositivo a otra red

</td><td>

### UI/UX
- **Sidebar colapsable** con 4 pestañas
- **Tema dark/light** + **idioma EN/ES**
- **Info-tips** en todos los controles
- **Responsive** (desktop + mobile)
- **UI optimista** + **LWT** online/offline

</td></tr>
</table>

---

## Firmware pre-compilado

Descarga la imagen binaria lista para flashear desde [GitHub Releases](https://github.com/JosePavasG/LED_DASHBOARD/releases/latest/download/XIAO_ESP32S3_Compilado.bin):

```bash
# Flashear XIAO ESP32S3 (flash completa de 8 MB)
python -m esptool --chip esp32s3 --port COM3 write_flash 0x0 XIAO_ESP32S3_Compilado.bin
```

> **Nota:** Después de flashear, aún necesitas crear `config.py` con tus credenciales WiFi y MQTT (ver sección [Setup → Firmware](#firmware)).

---

## Referencia esptool

Comandos esenciales para trabajar con placas ESP32.

### Identificar placa

```bash
# Detectar chip y MAC
python -m esptool chip_id

# Info completa (flash size, crystal, features)
python -m esptool flash_id
```

### Borrar flash

```bash
# Borrar toda la memoria flash (recomendado antes de flashear MicroPython)
python -m esptool --chip esp32s3 --port COM3 erase_flash

# ESP32 clásico (WROOM/WROVER)
python -m esptool --chip esp32 --port COM3 erase_flash
```

### Flashear firmware

```bash
# ESP32-S3 (XIAO, 8 MB flash)
python -m esptool --chip esp32s3 --port COM3 write_flash 0x0 firmware.bin

# ESP32 clásico (WROOM, 4 MB flash)
python -m esptool --chip esp32 --port COM3 write_flash -z 0x1000 firmware.bin

# ESP32-C3
python -m esptool --chip esp32c3 --port COM3 write_flash 0x0 firmware.bin
```

> **Tip:** La dirección de inicio varía por chip: `0x0` para S3/C3, `0x1000` para ESP32 clásico.

### Leer / respaldar flash

```bash
# Respaldar flash completa ESP32-S3 (8 MB)
python -m esptool --chip esp32s3 --port COM3 read_flash 0 0x800000 backup_s3.bin

# Respaldar flash ESP32 clásico (4 MB)
python -m esptool --chip esp32 --port COM3 read_flash 0 0x400000 backup_esp32.bin
```

### Tamaños de flash comunes

| Chip | Flash | Hex size | Dirección de inicio |
|------|-------|----------|---------------------|
| ESP32 (WROOM) | 4 MB | `0x400000` | `0x1000` |
| ESP32-S2 | 4 MB | `0x400000` | `0x0` |
| ESP32-S3 (XIAO) | 8 MB | `0x800000` | `0x0` |
| ESP32-C3 | 4 MB | `0x400000` | `0x0` |

---

## Estructura del proyecto

```
firmware/
├── boot.py                # Boot temprano + FW_VERSION
├── main.py                # WiFi, MQTT, LED, telemetría
├── config.example.py      # Template (copiar a config.py)
└── lib/
    ├── config_store.py    # Config runtime + persistencia JSON
    ├── boot_log.py        # Boot counter + crash log (NVS)
    ├── morse.py           # Morse no-bloqueante (ITU timing)
    └── webserver.py       # HTTP server no-bloqueante

web/
└── index.html             # Dashboard (HTML+CSS+JS, single-file)

mosquitto/config/          # Configuración del broker
nginx/                     # Reverse proxy + WebSocket
docker-compose.yml         # Mosquitto + Nginx
```

---

## Hardware

| Componente | Detalle |
|------------|---------|
| **Placa** | Seeed Studio XIAO ESP32S3 |
| **LED** | GPIO 21 (activo bajo) |
| **PWM** | 1000 Hz, 10-bit (0–1023) |

---

## Setup

### Docker (broker + dashboard)

```bash
docker compose up -d
```

Levanta:
- **Mosquitto** en puertos `1883` (MQTT) y `9001` (WebSocket)
- **Nginx** en puerto `80` sirviendo dashboard + proxy WebSocket

Accede al dashboard en `http://localhost`.

### Firmware

1. Instala [MicroPython](https://micropython.org/) en la XIAO ESP32S3
2. Copia `config.example.py` → `config.py` y edita credenciales
3. Sube los archivos:

```bash
mpremote cp firmware/boot.py :boot.py
mpremote cp firmware/main.py :main.py
mpremote cp firmware/config.py :config.py
mpremote mkdir :lib
mpremote cp firmware/lib/config_store.py :lib/config_store.py
mpremote cp firmware/lib/boot_log.py :lib/boot_log.py
mpremote cp firmware/lib/morse.py :lib/morse.py
mpremote cp firmware/lib/webserver.py :lib/webserver.py
```

4. (Opcional) Servir dashboard desde el ESP32:

```bash
mpremote mkdir :web
mpremote cp web/index.html :web/index.html
```

---

## Tópicos MQTT

Prefijo: `d/{MAC}/` donde MAC = `AA-BB-CC-DD-EE-FF`

| Tópico | Dirección | Descripción |
|--------|-----------|-------------|
| `d/{MAC}/led/cmd` | Dashboard → Device | Comandos de control |
| `d/{MAC}/led/status` | Device → Dashboard | Estado JSON (retained) |
| `d/{MAC}/device/telemetry` | Device → Dashboard | Telemetría periódica |
| `d/{MAC}/device/online` | Device → Dashboard | LWT online/offline (retained) |
| `d/{MAC}/config/set` | Dashboard → Device | Enviar nueva configuración |
| `d/{MAC}/config/current` | Device → Dashboard | Config actual (retained) |
| `d/{MAC}/config/ack` | Device → Dashboard | ACK de config |
| `d/{MAC}/wifi/scan` | Dashboard → Device | Solicitar escaneo WiFi |
| `d/{MAC}/wifi/scan_results` | Device → Dashboard | Resultados del escaneo |
| `d/{MAC}/wifi/forget` | Dashboard → Device | Borrar config.json y reiniciar |

### Comandos LED

Publicar en `d/{MAC}/led/cmd`:

| Comando | Descripción |
|---------|-------------|
| `on` | Enciende el LED |
| `off` | Apaga el LED |
| `toggle` | Alterna on/off |
| `breathe` | Respiración cíclica |
| `blink` | Parpadeo (1 Hz) |
| `strobe` | Parpadeo rápido (10 Hz) |
| `sos` | Patrón SOS en morse |
| `fade_in` | Encendido gradual |
| `fade_out` | Apagado gradual |
| `brightness:0..100` | Ajustar brillo |
| `morse:TEXTO` | Transmitir en morse |
