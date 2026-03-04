"""
Config Store — Runtime config con persistencia JSON
====================================================
Carga /config.json al arrancar, valida tipos/rangos, y aplica
via setattr() al modulo config para que el codigo existente
(config.BREATHE_PERIOD_MS, etc.) siga funcionando sin cambios.

Uso:
    import config_store
    config_store.load()                          # en boot.py
    config_store.validate_and_apply({"key": v})  # via MQTT
    config_store.get_all()                       # para publicar
"""

import json
import config

_CONFIG_FILE = "/config.json"

# Schema: key -> (tipo, min, max, requiere_restart)
# min/max solo aplican a int; None = sin limite
_SCHEMA = {
    "wifi_ssid":            (str, None, None, True),
    "wifi_password":        (str, None, None, True),
    "mqtt_broker":          (str, None, None, True),
    "mqtt_port":            (int, 1,    65535, True),
    "breathe_period_ms":    (int, 100,  30000, False),
    "blink_period_ms":      (int, 100,  30000, False),
    "strobe_period_ms":     (int, 20,   5000,  False),
    "sos_unit_ms":          (int, 50,   2000,  False),
    "morse_unit_ms":        (int, 50,   1000,  False),
    "telemetry_interval_s": (int, 1,    300,   False),
    "device_name":          (str, None, None,  False),
}

# key config_store -> atributo del modulo config
_KEY_TO_ATTR = {
    "wifi_ssid":            "WIFI_SSID",
    "wifi_password":        "WIFI_PASSWORD",
    "mqtt_broker":          "MQTT_BROKER",
    "mqtt_port":            "MQTT_PORT",
    "breathe_period_ms":    "BREATHE_PERIOD_MS",
    "blink_period_ms":      "BLINK_PERIOD_MS",
    "strobe_period_ms":     "STROBE_PERIOD_MS",
    "sos_unit_ms":          "SOS_UNIT_MS",
    "morse_unit_ms":        "MORSE_UNIT_MS",
    "telemetry_interval_s": "TELEMETRY_INTERVAL_S",
    "device_name":          "DEVICE_NAME",
}

# Snapshot de defaults al importar — antes de que load() modifique config.*
# Esto asegura que si load() se llama multiples veces, los defaults
# siempre son los originales de config.py, no los ya modificados.
_DEFAULTS = {}
for _k, _a in _KEY_TO_ATTR.items():
    _DEFAULTS[_k] = getattr(config, _a, None)

_runtime = {}


def load():
    """Carga config: defaults de config.py -> override con /config.json."""
    global _runtime
    _runtime = dict(_DEFAULTS)
    try:
        with open(_CONFIG_FILE, "r") as f:
            saved = json.load(f)
        for k, v in saved.items():
            if k in _SCHEMA:
                _runtime[k] = v
    except OSError:
        pass  # No config.json yet — use defaults
    except ValueError as e:
        print("[Config] JSON corrupto, usando defaults: {}".format(e))
    _apply_to_config()


def save():
    """Persiste config actual a /config.json."""
    try:
        with open(_CONFIG_FILE, "w") as f:
            json.dump(_runtime, f)
    except OSError as e:
        print("[Config] Error guardando: {}".format(e))


def get_all():
    """Retorna copia del dict runtime para publicar por MQTT."""
    return dict(_runtime)


def validate_and_apply(new_values):
    """Valida nuevos valores, aplica los validos, persiste.

    Retorna: (applied_dict, errors_list, needs_restart_bool)
    """
    applied = {}
    errors = []
    needs_restart = False

    for key, val in new_values.items():
        if key not in _SCHEMA:
            errors.append("{}: clave desconocida".format(key))
            continue

        typ, vmin, vmax, restart = _SCHEMA[key]

        if typ == int:
            try:
                val = int(val)
            except (ValueError, TypeError):
                errors.append("{}: debe ser entero".format(key))
                continue
            if vmin is not None and val < vmin:
                errors.append("{}: minimo {}".format(key, vmin))
                continue
            if vmax is not None and val > vmax:
                errors.append("{}: maximo {}".format(key, vmax))
                continue
        elif typ == str:
            val = str(val)

        _runtime[key] = val
        applied[key] = val
        if restart:
            needs_restart = True

    if applied:
        _apply_to_config()
        save()

    return applied, errors, needs_restart


def _apply_to_config():
    """Sincroniza _runtime -> atributos del modulo config."""
    for key, val in _runtime.items():
        attr = _KEY_TO_ATTR.get(key)
        if attr:
            setattr(config, attr, val)
