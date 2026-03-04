"""
Web Server — HTTP no-bloqueante para servir dashboard
=====================================================
Socket no-bloqueante, un cliente a la vez, envio en chunks de 1KB.
Maquina de estados explicita para claridad y debugging.

Estados:
    IDLE    -> esperando accept()
    RECV    -> cliente conectado, esperando request HTTP
    SENDING -> enviando body en chunks de 1KB
    (fin)   -> cierra cliente, vuelve a IDLE

Uso:
    import webserver
    webserver.start(80)    # despues de WiFi connect
    webserver.poll()       # en cada iteracion del loop (~5ms)
    webserver.stop()       # en shutdown
"""

import socket
import os

# Estados
_ST_IDLE = 0
_ST_RECV = 1
_ST_SENDING = 2

_CHUNK_SIZE = 1024
_HTML_PATH = "/web/index.html"

_srv = None
_client = None
_file = None
_remaining = 0
_state = _ST_IDLE


def start(port=80):
    """Crea socket listener no-bloqueante en el puerto indicado."""
    global _srv, _state
    _srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    _srv.bind(("0.0.0.0", port))
    _srv.listen(1)
    _srv.setblocking(False)
    _state = _ST_IDLE
    print("[Web] Servidor en puerto {}".format(port))


def poll():
    """Ejecuta un paso de la maquina de estados. No-bloqueante."""
    if _srv is None:
        return

    if _state == _ST_IDLE:
        _poll_accept()
    elif _state == _ST_RECV:
        _poll_recv()
    elif _state == _ST_SENDING:
        _poll_send_chunk()


def _poll_accept():
    """IDLE: intenta aceptar nueva conexion."""
    global _client, _state
    try:
        _client, addr = _srv.accept()
        _client.setblocking(False)
        _state = _ST_RECV
    except OSError:
        pass


def _poll_recv():
    """RECV: lee request HTTP, envia header, abre archivo."""
    global _file, _remaining, _state
    try:
        req = _client.recv(512)
        if not req:
            _cleanup()
            return
    except OSError:
        return

    # Obtener tamano del archivo
    try:
        size = os.stat(_HTML_PATH)[6]
    except OSError:
        try:
            _client.send(b"HTTP/1.0 404 Not Found\r\n\r\nFile not found")
        except OSError:
            pass
        _cleanup()
        return

    # Enviar header HTTP
    header = (
        "HTTP/1.0 200 OK\r\n"
        "Content-Type: text/html; charset=utf-8\r\n"
        "Content-Length: {}\r\n"
        "Connection: close\r\n"
        "\r\n"
    ).format(size)
    try:
        _client.send(header.encode())
    except OSError:
        _cleanup()
        return

    _file = open(_HTML_PATH, "rb")
    _remaining = size
    _state = _ST_SENDING


def _poll_send_chunk():
    """SENDING: envia un chunk de 1KB del archivo."""
    global _remaining

    if _remaining <= 0:
        _cleanup()
        return

    try:
        data = _file.read(min(_CHUNK_SIZE, _remaining))
        if data:
            _client.send(data)
            _remaining -= len(data)
        else:
            _remaining = 0
    except OSError:
        _cleanup()
        return

    if _remaining <= 0:
        _cleanup()


def _cleanup():
    """Cierra cliente y archivo, vuelve a IDLE."""
    global _client, _file, _remaining, _state
    if _file:
        try:
            _file.close()
        except Exception:
            pass
        _file = None
    if _client:
        try:
            _client.close()
        except Exception:
            pass
        _client = None
    _remaining = 0
    _state = _ST_IDLE


def stop():
    """Cierra el servidor completamente."""
    global _srv
    _cleanup()
    if _srv:
        try:
            _srv.close()
        except Exception:
            pass
        _srv = None
