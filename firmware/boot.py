"""
boot.py — Inicializacion temprana del sistema
==============================================
MicroPython ejecuta: _boot.py (interno) -> boot.py -> main.py -> REPL

Reglas de boot.py (docs oficiales):
  - DEBE terminar, NUNCA loop infinito
  - Solo init esencial que necesita correr antes de main.py
  - Si falla aqui, puede soft-brick (Ctrl+C para interrumpir)

Aqui hacemos:
  1. config_store.load() — para que main.py vea config persistida
  2. boot_log.init()     — incrementar boot counter (NVS atomico)

NO poner aqui: WiFi, MQTT, sockets, nada que pueda bloquear.

Ref: https://docs.micropython.org/en/latest/reference/reset_boot.html
"""

# ---- VERSION (cambiar aqui antes de cada release) ----
FW_VERSION = "1.0.0"
# -------------------------------------------------------

import gc
gc.collect()

print()
print("  FW v{} | XIAO ESP32S3 LED Dashboard".format(FW_VERSION))
print()

# Envolver en try/except para que un error aqui no impida el boot.
# Si config o boot_log fallan, main.py arranca con defaults.
try:
    import config_store
    config_store.load()
except Exception as e:
    print("[boot] config_store error: {}".format(e))

try:
    import boot_log
    boot_log.init()
except Exception as e:
    print("[boot] boot_log error: {}".format(e))

gc.collect()
