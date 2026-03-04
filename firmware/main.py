"""
MQTT LED Effects Dashboard — Seeed Studio XIAO ESP32S3
=======================================================
Control de LED con efectos PWM, telemetria, config remota,
morse libre y web server integrado.

Secuencia de arranque (MicroPython):
    _boot.py  -> init interno del firmware
    boot.py   -> config_store.load(), boot_log.init()
    main.py   -> WiFi, MQTT, web server, loop principal (este archivo)

Modulos en /lib/ (en sys.path de ESP32 por defecto):
    config_store, boot_log, morse, webserver

El loop es sincrono con polling no-bloqueante (~5ms por iteracion).
No se usa uasyncio para mantener bajo consumo de RAM (~20KB).

Ref: https://docs.micropython.org/en/latest/reference/reset_boot.html
"""

import sys
from machine import Pin, PWM, WDT, reset
import network
import time
import gc
import json
import os
import esp32
import ubinascii

try:
    from umqtt.simple import MQTTClient
except ImportError:
    from umqtt.robust import MQTTClient

import config
import config_store
import boot_log
import morse
import webserver

# Cached at import — boot.py already ran, so the module is loaded
_FW_VERSION = getattr(sys.modules.get('boot'), 'FW_VERSION', '0.0.0')


# ---------------------------------------------------------------
# MAC / Topic globals — populated after WiFi connects
# ---------------------------------------------------------------
_mac_str = ""       # "AA:BB:CC:DD:EE:FF"
_mac_topic = ""     # "AA-BB-CC-DD-EE-FF"
_topics = {}        # built by _build_topics()


def _build_topics():
    """Build all MQTT topic byte-strings from MAC address.
    Call after wifi_connect() so wlan.config('mac') is available."""
    global _mac_str, _mac_topic, _topics

    raw = wlan.config('mac')
    _mac_str = ubinascii.hexlify(raw, ':').decode().upper()
    _mac_topic = _mac_str.replace(':', '-')

    prefix = getattr(config, 'MQTT_TOPIC_PREFIX', 'd/{mac}').replace("{mac}", _mac_topic)

    _topics = {
        'cmd':          (prefix + "/led/cmd").encode(),
        'status':       (prefix + "/led/status").encode(),
        'telemetry':    (prefix + "/device/telemetry").encode(),
        'online':       (prefix + "/device/online").encode(),
        'config_set':   (prefix + "/config/set").encode(),
        'config_cur':   (prefix + "/config/current").encode(),
        'config_ack':   (prefix + "/config/ack").encode(),
        'wifi_scan':    (prefix + "/wifi/scan").encode(),
        'wifi_scan_res':(prefix + "/wifi/scan_results").encode(),
    }

    # Auto-generate client ID from MAC if empty
    if not config.MQTT_CLIENT_ID:
        config.MQTT_CLIENT_ID = "esp32_" + _mac_topic

    print("[Topics] Prefix: {}".format(prefix))


# ---------------------------------------------------------------
# PWM LED — init diferido hasta main() para que config_store.load()
#           (en boot.py) haya aplicado los valores persistidos
# ---------------------------------------------------------------
_pwm = None
_brightness = 100
_led_on = False
_current_effect = "none"
_effect_last_ms = 0


def _init_pwm():
    """Inicializa PWM del LED. Llamar despues de config_store.load()."""
    global _pwm
    _pwm = PWM(Pin(config.LED_PIN), freq=config.PWM_FREQ, duty=0)


def _duty_from_percent(pct):
    """Curva cuadratica para percepcion natural de brillo."""
    v = int((pct / 100.0) ** 2 * config.PWM_MAX_DUTY)
    if config.LED_ACTIVE_LOW:
        v = config.PWM_MAX_DUTY - v
    return v


def led_set_raw(pct):
    """Pone el LED a un % de brillo (0-100) inmediatamente."""
    _pwm.duty(int(_duty_from_percent(pct)))


def led_on():
    global _led_on, _current_effect
    _current_effect = "none"
    _led_on = True
    led_set_raw(_brightness)


def led_off():
    global _led_on, _current_effect
    _current_effect = "none"
    _led_on = False
    led_set_raw(0)


def led_toggle():
    if _led_on and _current_effect == "none":
        led_off()
    else:
        led_on()


def set_brightness(val):
    global _brightness
    _brightness = max(0, min(100, val))
    if _led_on and _current_effect == "none":
        led_set_raw(_brightness)


def start_effect(name):
    global _current_effect, _effect_last_ms, _led_on
    _current_effect = name
    _effect_last_ms = time.ticks_ms()
    _led_on = True


# ---------------------------------------------------------------
# Efectos no-bloqueantes
# ---------------------------------------------------------------
def _tick_breathe(now):
    period = config.BREATHE_PERIOD_MS
    elapsed = time.ticks_diff(now, _effect_last_ms)
    pos = elapsed % period
    half = period // 2
    if pos < half:
        pct = pos / half
    else:
        pct = 1.0 - (pos - half) / half
    led_set_raw(pct * _brightness)


def _tick_blink(now):
    elapsed = time.ticks_diff(now, _effect_last_ms)
    half = config.BLINK_PERIOD_MS // 2
    if (elapsed // half) % 2 == 0:
        led_set_raw(_brightness)
    else:
        led_set_raw(0)


def _tick_strobe(now):
    elapsed = time.ticks_diff(now, _effect_last_ms)
    half = config.STROBE_PERIOD_MS // 2
    if (elapsed // half) % 2 == 0:
        led_set_raw(_brightness)
    else:
        led_set_raw(0)


_SOS_PATTERN = [
    1, 1, 1, 1, 1, 3,  # S: . . .
    3, 1, 3, 1, 3, 3,  # O: - - -
    1, 1, 1, 1, 1, 7,  # S: . . . (word gap)
]


def _tick_sos(now):
    global _effect_last_ms
    unit = config.SOS_UNIT_MS
    elapsed = time.ticks_diff(now, _effect_last_ms)

    acc = 0
    step = 0
    for i in range(len(_SOS_PATTERN)):
        dur = _SOS_PATTERN[i] * unit
        if elapsed < acc + dur:
            step = i
            break
        acc += dur
    else:
        _effect_last_ms = now
        step = 0

    led_set_raw(_brightness if step % 2 == 0 else 0)


def _tick_fade_in(now):
    global _current_effect, _led_on
    elapsed = time.ticks_diff(now, _effect_last_ms)
    duration = config.BREATHE_PERIOD_MS // 2
    if elapsed >= duration:
        led_set_raw(_brightness)
        _current_effect = "none"
        _led_on = True
        return
    led_set_raw((elapsed / duration) * _brightness)


def _tick_fade_out(now):
    global _current_effect, _led_on
    elapsed = time.ticks_diff(now, _effect_last_ms)
    duration = config.BREATHE_PERIOD_MS // 2
    if elapsed >= duration:
        led_set_raw(0)
        _current_effect = "none"
        _led_on = False
        return
    led_set_raw((1.0 - elapsed / duration) * _brightness)


def _tick_morse(now):
    global _current_effect, _led_on
    if not morse.tick(now, led_set_raw, _brightness):
        _current_effect = "none"
        _led_on = False
        led_set_raw(0)
        mqtt_publish_status()


_EFFECT_TICKERS = {
    "breathe":  _tick_breathe,
    "blink":    _tick_blink,
    "strobe":   _tick_strobe,
    "sos":      _tick_sos,
    "fade_in":  _tick_fade_in,
    "fade_out": _tick_fade_out,
    "morse":    _tick_morse,
}


def tick_effect():
    """Llamar en cada iteracion del loop. Avanza el efecto activo."""
    ticker = _EFFECT_TICKERS.get(_current_effect)
    if ticker:
        ticker(time.ticks_ms())


# ---------------------------------------------------------------
# WiFi
# ---------------------------------------------------------------
wlan = network.WLAN(network.STA_IF)


def wifi_connect():
    if wlan.isconnected():
        return True
    wlan.active(True)
    wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
    print("Conectando a WiFi '{}'".format(config.WIFI_SSID), end="")
    t0 = time.time()
    while not wlan.isconnected():
        if time.time() - t0 > config.WIFI_TIMEOUT_S:
            print(" TIMEOUT")
            return False
        print(".", end="")
        time.sleep(1)
    print(" OK — IP: {}".format(wlan.ifconfig()[0]))
    return True


def wifi_ensure():
    if not wlan.isconnected():
        print("[WiFi] Reconectando...")
        wlan.active(False)
        time.sleep(1)
        return wifi_connect()
    return True


# ---------------------------------------------------------------
# MQTT
# ---------------------------------------------------------------
client = None
_pending_restart = False


def _build_status_json():
    d = {
        "effect": _current_effect,
        "brightness": _brightness,
        "led_on": _led_on,
    }
    if _current_effect == "morse":
        d["morse_text"] = morse.get_text()
    return json.dumps(d)


# --- Dispatch table para comandos MQTT ---
def _cmd_on(_msg):
    led_on()

def _cmd_off(_msg):
    led_off()

def _cmd_toggle(_msg):
    led_toggle()

def _cmd_effect(msg):
    start_effect(msg)

def _cmd_brightness(msg):
    try:
        val = int(msg.split(":")[1])
        set_brightness(val)
    except ValueError:
        print("  Valor de brillo invalido")

def _cmd_morse(msg_original):
    global _current_effect, _led_on
    text = msg_original[6:]  # preservar case original
    if text:
        morse.start(text, time.ticks_ms())
        _current_effect = "morse"
        _led_on = True
        print("  Morse: '{}'".format(text))


_CMD_DISPATCH = {
    "on":       _cmd_on,
    "off":      _cmd_off,
    "toggle":   _cmd_toggle,
    "breathe":  _cmd_effect,
    "blink":    _cmd_effect,
    "strobe":   _cmd_effect,
    "sos":      _cmd_effect,
    "fade_in":  _cmd_effect,
    "fade_out": _cmd_effect,
}


def mqtt_callback(topic, msg):
    msg_str = msg.decode().strip()

    # WiFi scan handler
    if topic == _topics['wifi_scan']:
        _handle_wifi_scan()
        return

    # Config set handler (topic separado)
    if topic == _topics['config_set']:
        _handle_config_set(msg_str)
        return

    msg_lower = msg_str.lower()
    print("[MQTT] {} -> '{}'".format(topic.decode(), msg_lower))

    # Buscar en dispatch table
    handler = _CMD_DISPATCH.get(msg_lower)
    if handler:
        handler(msg_lower)
    elif msg_lower.startswith("brightness:"):
        _cmd_brightness(msg_lower)
    elif msg_lower.startswith("morse:"):
        _cmd_morse(msg_str)  # case original
    else:
        print("  Comando no reconocido")
        return

    print("  LED: {} | Efecto: {} | Brillo: {}%".format(
        "ON" if _led_on else "OFF", _current_effect, _brightness))
    mqtt_publish_status()


def _handle_wifi_scan():
    """Escanea redes WiFi y publica resultados en MQTT."""
    print("[WiFi] Escaneando redes...")
    try:
        nets = wlan.scan()
        results = []
        seen = set()
        for ssid, _bssid, ch, rssi, auth, _hidden in nets:
            name = ssid.decode() if isinstance(ssid, bytes) else str(ssid)
            if not name or name in seen:
                continue
            seen.add(name)
            results.append({"ssid": name, "rssi": rssi, "auth": auth, "ch": ch})
        results.sort(key=lambda x: x["rssi"], reverse=True)
        payload = json.dumps(results)
        client.publish(_topics['wifi_scan_res'], payload.encode())
        print("[WiFi] {} redes encontradas".format(len(results)))
    except Exception as e:
        print("[WiFi] Error en scan: {}".format(e))


def _handle_config_set(msg_str):
    """Procesa JSON de config/set, valida, aplica, publica ACK."""
    global _pending_restart
    try:
        new_values = json.loads(msg_str)
    except ValueError:
        _publish_config_ack(False, ["JSON invalido"], False)
        return

    applied, errors, needs_restart = config_store.validate_and_apply(new_values)
    _publish_config_ack(bool(applied), errors, needs_restart)
    mqtt_publish_config()

    if needs_restart and applied:
        _pending_restart = True
        print("[Config] Restart pendiente en 2s...")


def _publish_config_ack(success, errors, restarting):
    if not client:
        return
    ack = json.dumps({
        "success": success,
        "errors": errors,
        "restarting": restarting,
    })
    try:
        client.publish(_topics['config_ack'], ack.encode())
    except Exception as e:
        print("[MQTT] Error publicando ACK: {}".format(e))


def mqtt_publish_status():
    if not client:
        return
    try:
        client.publish(_topics['status'], _build_status_json().encode(), retain=True)
    except Exception as e:
        print("[MQTT] Error publicando status: {}".format(e))


def mqtt_publish_config():
    """Publica config actual (retained) para que el dashboard la lea."""
    if not client:
        return
    try:
        data = json.dumps(config_store.get_all())
        client.publish(_topics['config_cur'], data.encode(), retain=True)
    except Exception as e:
        print("[MQTT] Error publicando config: {}".format(e))


def _read_temp():
    try:
        return esp32.mcu_temperature()
    except Exception:
        return 0


def mqtt_publish_telemetry():
    if not client:
        return
    rssi = wlan.status("rssi") if wlan.isconnected() else 0
    fs = os.statvfs('/')
    data = json.dumps({
        "rssi": rssi,
        "ssid": config.WIFI_SSID,
        "uptime": time.time(),
        "free_ram": gc.mem_free(),
        "fs_free": fs[0] * fs[3],
        "fs_total": fs[0] * fs[2],
        "temp_c": _read_temp(),
        "ip": wlan.ifconfig()[0] if wlan.isconnected() else "0.0.0.0",
        "mac": _mac_str,
        "device_name": getattr(config, 'DEVICE_NAME', '') or _mac_str,
        "fw_version": _FW_VERSION,
    })
    try:
        client.publish(_topics['telemetry'], data.encode())
    except Exception as e:
        print("[MQTT] Error publicando telemetria: {}".format(e))


def mqtt_connect():
    global client

    client = MQTTClient(
        config.MQTT_CLIENT_ID,
        config.MQTT_BROKER,
        port=config.MQTT_PORT,
        user=config.MQTT_USER or None,
        password=config.MQTT_PASSWORD or None,
        keepalive=config.MQTT_KEEPALIVE,
    )

    client.set_last_will(_topics['online'], b"offline", retain=True)
    client.set_callback(mqtt_callback)

    print("[MQTT] Conectando a {}:{}".format(config.MQTT_BROKER, config.MQTT_PORT))
    client.connect()
    print("[MQTT] Conectado OK")

    client.publish(_topics['online'], b"online", retain=True)
    client.subscribe(_topics['cmd'])
    print("[MQTT] Suscrito a: {}".format(_topics['cmd'].decode()))
    time.sleep_ms(50)
    client.subscribe(_topics['config_set'])
    print("[MQTT] Suscrito a: {}".format(_topics['config_set'].decode()))
    time.sleep_ms(50)
    client.subscribe(_topics['wifi_scan'])
    print("[MQTT] Suscrito a: {}".format(_topics['wifi_scan'].decode()))
    time.sleep_ms(50)
    mqtt_publish_status()


def mqtt_ensure():
    try:
        client.ping()
        return True
    except Exception:
        print("[MQTT] Reconectando...")
        try:
            mqtt_connect()
            return True
        except Exception as e:
            print("[MQTT] Error: {}".format(e))
            boot_log.log_crash(e)
            return False


# ---------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------
def main():
    global _pending_restart

    # boot.py ya ejecuto config_store.load() y boot_log.init()
    # Inicializar hardware con config ya cargada
    _init_pwm()

    # Parpadeo de arranque (3 blinks rapidos)
    for _ in range(3):
        led_set_raw(100)
        time.sleep_ms(100)
        led_set_raw(0)
        time.sleep_ms(100)

    print()
    print("=" * 50)
    print("  Boot #{}".format(boot_log.get_boot_count()))
    print("=" * 50)
    print()

    # WiFi
    if not wifi_connect():
        print("[ERROR] No WiFi — reiniciando en 10s")
        time.sleep(10)
        reset()

    # Build MAC-based topics (requires WiFi to be connected)
    _build_topics()

    # Web server (no-critico, no resetear si falla)
    try:
        webserver.start(80)
    except Exception as e:
        print("[Web] Error al iniciar: {}".format(e))

    # MQTT
    try:
        mqtt_connect()
    except Exception as e:
        print("[ERROR] MQTT: {}".format(e))
        boot_log.log_crash(e)
        time.sleep(10)
        reset()

    wdt = WDT(timeout=40000)

    print()
    print("Comandos: on, off, toggle, breathe, blink, strobe,")
    print("          sos, fade_in, fade_out, brightness:N, morse:TEXT")
    print()

    error_count = 0
    last_telemetry = time.time()
    last_health = time.ticks_ms()
    last_gc = time.ticks_ms()
    restart_at = 0
    config_published = False

    while True:
        try:
            wdt.feed()
            now_ms = time.ticks_ms()

            # Restart diferido (tras cambio de WiFi/broker)
            if _pending_restart:
                if restart_at == 0:
                    restart_at = now_ms
                elif time.ticks_diff(now_ms, restart_at) >= 2000:
                    print("[Config] Reiniciando...")
                    time.sleep_ms(100)
                    reset()

            # Health check cada 30s
            if time.ticks_diff(now_ms, last_health) >= 30000:
                last_health = now_ms
                if not wifi_ensure():
                    error_count += 1
                    time.sleep(5)
                    continue
                if not mqtt_ensure():
                    error_count += 1
                    time.sleep(5)
                    continue

            # Procesar mensajes MQTT entrantes
            client.check_msg()

            # Efectos LED
            tick_effect()

            # Web server (un chunk por iteracion)
            try:
                webserver.poll()
            except OSError:
                pass

            # GC periodico cada 10s
            if time.ticks_diff(now_ms, last_gc) >= 10000:
                gc.collect()
                last_gc = now_ms

            # Publicar config una vez (diferido del connect para no saturar)
            if not config_published:
                mqtt_publish_config()
                config_published = True

            # Telemetria periodica
            now = time.time()
            if now - last_telemetry >= config.TELEMETRY_INTERVAL_S:
                mqtt_publish_telemetry()
                last_telemetry = now

            error_count = 0
            time.sleep_ms(5)

        except KeyboardInterrupt:
            print("\nDetenido por usuario")
            led_off()
            try:
                client.publish(_topics['online'], b"offline", retain=True)
                client.disconnect()
            except OSError:
                pass
            webserver.stop()
            break

        except Exception as e:
            sys.print_exception(e)
            boot_log.log_crash(e)
            error_count += 1

        if error_count >= 5:
            print("Demasiados errores consecutivos. Reiniciando...")
            time.sleep(2)
            reset()


if __name__ == "__main__":
    main()
