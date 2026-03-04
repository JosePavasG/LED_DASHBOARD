"""
Boot Log — Boot counter + crash log via NVS
============================================
Usa esp32.NVS (Non-Volatile Storage) para persistencia atomica.
NVS sobrevive crashes, resets y reflashes (a diferencia de archivos).

Uso:
    import boot_log
    boot_log.init()                    # en boot.py (antes de main)
    boot_log.log_crash(exception)      # en except del loop principal
    boot_log.get_boot_count()          # para telemetria
    boot_log.get_last_crash()          # para telemetria
"""

import json
import esp32

_NVS_NAMESPACE = "bootlog"
_MAX_CRASHES = 5
_MAX_CRASH_LEN = 80
_CRASH_BUF_SIZE = 512

_nvs = None
_boot_count = 0
_crashes = []


def init():
    """Incrementa boot counter y carga crash history desde NVS.

    Defensivo: si NVS esta corrupto, resetea valores en vez de fallar.
    Este modulo NUNCA debe impedir el boot.
    """
    global _nvs, _boot_count, _crashes

    try:
        _nvs = esp32.NVS(_NVS_NAMESPACE)
    except OSError as e:
        print("[Boot] NVS init error: {}".format(e))
        return

    # Boot counter (i32, atomico)
    try:
        _boot_count = _nvs.get_i32("boots")
    except OSError:
        _boot_count = 0

    _boot_count += 1

    try:
        _nvs.set_i32("boots", _boot_count)
        _nvs.commit()
    except OSError as e:
        print("[Boot] Error persistiendo boot count: {}".format(e))

    # Crash log (blob -> JSON array de strings)
    try:
        buf = bytearray(_CRASH_BUF_SIZE)
        length = _nvs.get_blob("crashes", buf)
        _crashes = json.loads(buf[:length].decode())
        if not isinstance(_crashes, list):
            _crashes = []
    except (OSError, ValueError, TypeError):
        _crashes = []

    print("[Boot] #{} | Crashes almacenados: {}".format(
        _boot_count, len(_crashes)))


def log_crash(exc):
    """Registra un crash en NVS (max 5, truncado a 80 chars).

    Seguro para llamar incluso si init() fallo parcialmente.
    """
    global _crashes

    if _nvs is None:
        print("[Boot] NVS no disponible, crash no guardado")
        return

    msg = str(exc)[:_MAX_CRASH_LEN]
    _crashes.append(msg)
    if len(_crashes) > _MAX_CRASHES:
        _crashes = _crashes[-_MAX_CRASHES:]

    try:
        data = json.dumps(_crashes).encode()
        _nvs.set_blob("crashes", data)
        _nvs.commit()
    except OSError as e:
        print("[Boot] Error guardando crash: {}".format(e))


def get_boot_count():
    """Retorna numero de boots desde que se flasheo."""
    return _boot_count


def get_last_crash():
    """Retorna ultimo crash como string, o None si no hay."""
    return _crashes[-1] if _crashes else None


def get_crashes():
    """Retorna lista de crashes (max 5)."""
    return list(_crashes)
