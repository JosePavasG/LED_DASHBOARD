"""
Configuracion WiFi y MQTT
==========================
1. Copiar a config.py:     cp config.example.py config.py
2. Editar credenciales en config.py
3. Subir a la placa:       mpremote cp firmware/config.py :config.py

config.py esta en .gitignore — nunca se commitea al repo.
Los valores aqui son defaults que config_store.py puede sobreescribir
en runtime via MQTT (persistidos en /config.json en el dispositivo).
"""

# ---------------------------------------------------------------
# WiFi
# ---------------------------------------------------------------
WIFI_SSID = "TU_SSID"
WIFI_PASSWORD = "TU_PASSWORD"
WIFI_TIMEOUT_S = 15

# ---------------------------------------------------------------
# MQTT - Broker Mosquitto local (Docker)
# Cambiar MQTT_BROKER a la IP de la maquina que corre Docker
# ---------------------------------------------------------------
MQTT_BROKER = "192.168.1.100"
MQTT_PORT = 1883
MQTT_CLIENT_ID = ""                     # auto-generated from MAC if empty
MQTT_USER = ""
MQTT_PASSWORD = ""

# Topicos — {mac} se reemplaza en runtime con MAC hyphenated (AA-BB-CC-DD-EE-FF)
MQTT_TOPIC_PREFIX = "d/{mac}"

# Nombre amigable del dispositivo (opcional, se usa MAC si esta vacio)
DEVICE_NAME = ""

MQTT_KEEPALIVE = 60

# ---------------------------------------------------------------
# HARDWARE - XIAO ESP32S3
# ---------------------------------------------------------------
LED_PIN = 21
LED_ACTIVE_LOW = True

# ---------------------------------------------------------------
# PWM
# ---------------------------------------------------------------
PWM_FREQ = 1000
PWM_MAX_DUTY = 1023

# ---------------------------------------------------------------
# Timings de efectos (ms)
# ---------------------------------------------------------------
BREATHE_PERIOD_MS = 3000
BLINK_PERIOD_MS = 1000
STROBE_PERIOD_MS = 100
SOS_UNIT_MS = 200
MORSE_UNIT_MS = 150

# ---------------------------------------------------------------
# Telemetria
# NOTA: FW_VERSION se define en boot.py (inicio del archivo)
# ---------------------------------------------------------------
TELEMETRY_INTERVAL_S = 5
