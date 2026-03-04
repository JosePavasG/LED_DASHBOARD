"""
Configuracion WiFi y MQTT
==========================
Editar con tus credenciales antes de subir a la placa.
"""

# ---------------------------------------------------------------
# WiFi
# ---------------------------------------------------------------
WIFI_SSID = ""       # Tu red WiFi
WIFI_PASSWORD = ""   # Tu contraseña WiFi
WIFI_TIMEOUT_S = 15

# ---------------------------------------------------------------
# MQTT - Broker publico HiveMQ (sin instalar nada)
# ---------------------------------------------------------------
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_CLIENT_ID = "xiao_esp32s3"
MQTT_USER = ""
MQTT_PASSWORD = ""

# Topicos (prefijo unico para evitar colisiones)
MQTT_TOPIC_CMD = b"xiao_pavas/led/cmd"
MQTT_TOPIC_STATUS = b"xiao_pavas/led/status"
MQTT_TOPIC_TELEMETRY = b"xiao_pavas/device/telemetry"
MQTT_TOPIC_ONLINE = b"xiao_pavas/device/online"

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

# ---------------------------------------------------------------
# Telemetria
# ---------------------------------------------------------------
TELEMETRY_INTERVAL_S = 5
