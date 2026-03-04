"""
MQTT LED Effects Dashboard - Seeed Studio XIAO ESP32S3
=======================================================
Control de LED con efectos PWM, telemetria en tiempo real y LWT.
Broker publico HiveMQ.
"""

from machine import Pin, PWM, WDT, reset
import network
import time
import gc
import json

try:
    from umqtt.simple import MQTTClient
except ImportError:
    from umqtt.robust import MQTTClient

import config


# ---------------------------------------------------------------
# PWM LED
# ---------------------------------------------------------------
_pwm = PWM(Pin(config.LED_PIN), freq=config.PWM_FREQ, duty=0)
_brightness = 100  # 0-100
_led_on = False
_current_effect = "none"
_effect_step = 0
_effect_last_ms = 0


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
    global _current_effect, _effect_step, _effect_last_ms, _led_on
    _current_effect = name
    _effect_step = 0
    _effect_last_ms = time.ticks_ms()
    _led_on = True


# ---------------------------------------------------------------
# Efectos no-bloqueantes
# ---------------------------------------------------------------
def _tick_breathe(now):
    global _effect_step, _effect_last_ms
    period = config.BREATHE_PERIOD_MS
    elapsed = time.ticks_diff(now, _effect_last_ms)
    # Posicion en el ciclo 0..period
    pos = elapsed % period
    half = period // 2
    if pos < half:
        pct = pos / half
    else:
        pct = 1.0 - (pos - half) / half
    led_set_raw(pct * _brightness)


def _tick_blink(now):
    global _effect_step, _effect_last_ms
    elapsed = time.ticks_diff(now, _effect_last_ms)
    half = config.BLINK_PERIOD_MS // 2
    if (elapsed // half) % 2 == 0:
        led_set_raw(_brightness)
    else:
        led_set_raw(0)


def _tick_strobe(now):
    global _effect_step, _effect_last_ms
    elapsed = time.ticks_diff(now, _effect_last_ms)
    half = config.STROBE_PERIOD_MS // 2
    if (elapsed // half) % 2 == 0:
        led_set_raw(_brightness)
    else:
        led_set_raw(0)


# SOS en morse: ... --- ...
# dot=1u, dash=3u, gap entre simbolos=1u, gap entre letras=3u, gap entre palabras=7u
_SOS_PATTERN = [
    1, 1, 1, 1, 1, 3,  # S: dot gap dot gap dot letter-gap
    3, 1, 3, 1, 3, 3,  # O: dash gap dash gap dash letter-gap
    1, 1, 1, 1, 1, 7,  # S: dot gap dot gap dot word-gap
]


def _tick_sos(now):
    global _effect_step, _effect_last_ms
    unit = config.SOS_UNIT_MS
    elapsed = time.ticks_diff(now, _effect_last_ms)
    # Calcular el paso actual en el patron
    total_steps = len(_SOS_PATTERN)
    # Calcular tiempo acumulado hasta cada paso
    acc = 0
    step = 0
    for i in range(total_steps):
        dur = _SOS_PATTERN[i] * unit
        if elapsed < acc + dur:
            step = i
            break
        acc += dur
    else:
        # Ciclo completo, reiniciar
        _effect_last_ms = now
        step = 0

    # Pasos pares = LED encendido, impares = LED apagado
    if step % 2 == 0:
        led_set_raw(_brightness)
    else:
        led_set_raw(0)


def _tick_fade_in(now):
    global _current_effect, _led_on
    elapsed = time.ticks_diff(now, _effect_last_ms)
    duration = config.BREATHE_PERIOD_MS // 2
    if elapsed >= duration:
        led_set_raw(_brightness)
        _current_effect = "none"
        _led_on = True
        return
    pct = elapsed / duration
    led_set_raw(pct * _brightness)


def _tick_fade_out(now):
    global _current_effect, _led_on
    elapsed = time.ticks_diff(now, _effect_last_ms)
    duration = config.BREATHE_PERIOD_MS // 2
    if elapsed >= duration:
        led_set_raw(0)
        _current_effect = "none"
        _led_on = False
        return
    pct = 1.0 - elapsed / duration
    led_set_raw(pct * _brightness)


_EFFECT_TICKERS = {
    "breathe": _tick_breathe,
    "blink": _tick_blink,
    "strobe": _tick_strobe,
    "sos": _tick_sos,
    "fade_in": _tick_fade_in,
    "fade_out": _tick_fade_out,
}


def tick_effect():
    """Llamar en cada iteracion del loop. Avanza el efecto activo."""
    if _current_effect in _EFFECT_TICKERS:
        _EFFECT_TICKERS[_current_effect](time.ticks_ms())


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
    start = time.time()
    while not wlan.isconnected():
        if time.time() - start > config.WIFI_TIMEOUT_S:
            print(" TIMEOUT")
            return False
        print(".", end="")
        time.sleep(1)
    print(" OK")
    print("  IP: {}".format(wlan.ifconfig()[0]))
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


def _build_status_json():
    return json.dumps({
        "effect": _current_effect,
        "brightness": _brightness,
        "led_on": _led_on,
    })


def mqtt_callback(topic, msg):
    msg_str = msg.decode().strip().lower()
    print("[MQTT] {} -> '{}'".format(topic.decode(), msg_str))

    if msg_str == "on":
        led_on()
    elif msg_str == "off":
        led_off()
    elif msg_str == "toggle":
        led_toggle()
    elif msg_str in ("breathe", "blink", "strobe", "sos", "fade_in", "fade_out"):
        start_effect(msg_str)
    elif msg_str.startswith("brightness:"):
        try:
            val = int(msg_str.split(":")[1])
            set_brightness(val)
        except ValueError:
            print("  Valor de brillo invalido")
            return
    else:
        print("  Comando no reconocido")
        return

    print("  LED: {} | Efecto: {} | Brillo: {}%".format(
        "ON" if _led_on else "OFF", _current_effect, _brightness))
    mqtt_publish_status()


def mqtt_publish_status():
    if client:
        try:
            client.publish(config.MQTT_TOPIC_STATUS, _build_status_json(), retain=True)
        except Exception as e:
            print("[MQTT] Error publicando status: {}".format(e))


def mqtt_publish_telemetry():
    if client:
        rssi = wlan.status("rssi") if wlan.isconnected() else 0
        data = json.dumps({
            "rssi": rssi,
            "uptime": time.time(),
            "free_ram": gc.mem_free(),
            "ip": wlan.ifconfig()[0] if wlan.isconnected() else "0.0.0.0",
        })
        try:
            client.publish(config.MQTT_TOPIC_TELEMETRY, data)
        except Exception as e:
            print("[MQTT] Error publicando telemetria: {}".format(e))


def mqtt_connect():
    global client

    client = MQTTClient(
        config.MQTT_CLIENT_ID,
        config.MQTT_BROKER,
        port=config.MQTT_PORT,
        user=config.MQTT_USER if config.MQTT_USER else None,
        password=config.MQTT_PASSWORD if config.MQTT_PASSWORD else None,
        keepalive=config.MQTT_KEEPALIVE,
    )

    # LWT: si el ESP32 se desconecta, el broker publica "offline"
    client.set_last_will(config.MQTT_TOPIC_ONLINE, b"offline", retain=True)
    client.set_callback(mqtt_callback)

    print("[MQTT] Conectando a {}:{}".format(config.MQTT_BROKER, config.MQTT_PORT))
    client.connect()
    print("[MQTT] Conectado OK")

    # Publicar "online" al conectar
    client.publish(config.MQTT_TOPIC_ONLINE, b"online", retain=True)

    client.subscribe(config.MQTT_TOPIC_CMD)
    print("[MQTT] Suscrito a: {}".format(config.MQTT_TOPIC_CMD.decode()))
    mqtt_publish_status()
    return True


def mqtt_ensure():
    global client
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
            return False


# ---------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------
def main():
    # Parpadeo de arranque
    for _ in range(3):
        led_set_raw(100)
        time.sleep_ms(100)
        led_set_raw(0)
        time.sleep_ms(100)

    print()
    print("=" * 50)
    print("  XIAO ESP32S3 - MQTT LED Effects Dashboard")
    print("=" * 50)
    print()

    if not wifi_connect():
        print("ERROR: No WiFi")
        time.sleep(10)
        reset()

    try:
        mqtt_connect()
    except Exception as e:
        print("ERROR MQTT: {}".format(e))
        time.sleep(10)
        reset()

    wdt = WDT(timeout=40000)

    print()
    print("Listo. Esperando comandos en '{}'".format(config.MQTT_TOPIC_CMD.decode()))
    print("Efectos: on, off, toggle, breathe, blink, strobe, sos, fade_in, fade_out")
    print("Brillo: brightness:0 .. brightness:100")
    print()

    error_count = 0
    last_telemetry = time.time()
    last_health = time.ticks_ms()
    last_gc = time.ticks_ms()

    while True:
        try:
            wdt.feed()

            now_ms = time.ticks_ms()

            # Chequeo de conectividad cada 30s (no cada loop)
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

            client.check_msg()

            # Avanzar efecto activo
            tick_effect()

            # GC periodico cada 10s (fuera de telemetria)
            if time.ticks_diff(now_ms, last_gc) >= 10000:
                gc.collect()
                last_gc = now_ms

            # Telemetria periodica
            now = time.time()
            if now - last_telemetry >= config.TELEMETRY_INTERVAL_S:
                mqtt_publish_telemetry()
                last_telemetry = now

            error_count = 0
            time.sleep_ms(5)

        except KeyboardInterrupt:
            print("\nDetenido")
            led_off()
            try:
                client.publish(config.MQTT_TOPIC_ONLINE, b"offline", retain=True)
                client.disconnect()
            except:
                pass
            break

        except Exception as e:
            print("[ERROR] {}".format(e))
            error_count += 1

        if error_count >= 5:
            print("Demasiados errores. Reiniciando...")
            time.sleep(2)
            reset()


if __name__ == "__main__":
    main()
