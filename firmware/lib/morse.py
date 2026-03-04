"""
Morse Code Generator — No-bloqueante
=====================================
Convierte texto a patron de duraciones ITU y lo transmite via tick().

Timing ITU estandar (en unidades de MORSE_UNIT_MS):
    dot = 1u ON, dash = 3u ON
    gap intra-caracter = 1u OFF
    gap inter-caracter = 3u OFF
    gap inter-palabra  = 7u OFF

Uso:
    import morse
    morse.start("SOS", time.ticks_ms())
    # en el loop:
    if not morse.tick(now_ms, led_set_raw, brightness):
        # transmision terminada
"""

import config
import time

# ITU Morse: letra -> string de dots y dashes
_CODE = {
    'A': '.-',    'B': '-...',  'C': '-.-.',  'D': '-..',
    'E': '.',     'F': '..-.',  'G': '--.',   'H': '....',
    'I': '..',    'J': '.---',  'K': '-.-',   'L': '.-..',
    'M': '--',    'N': '-.',    'O': '---',   'P': '.--.',
    'Q': '--.-',  'R': '.-.',   'S': '...',   'T': '-',
    'U': '..-',   'V': '...-',  'W': '.--',   'X': '-..-',
    'Y': '-.--',  'Z': '--..',
    '0': '-----', '1': '.----', '2': '..---', '3': '...--',
    '4': '....-', '5': '.....', '6': '-....', '7': '--...',
    '8': '---..', '9': '----.',
    '.': '.-.-.-', ',': '--..--', '?': '..--..', "'": '.----.',
    '!': '-.-.--', '/': '-..-.', '(': '-.--.', ')': '-.--.-',
    '&': '.-...', ':': '---...', ';': '-.-.-.', '=': '-...-',
    '+': '.-.-.', '-': '-....-', '_': '..--.-', '"': '.-..-.',
    '$': '...-..-', '@': '.--.-.',
}

_MAX_LEN = 100

# Pattern: list of (duration_units, is_on)
_pattern = []
_index = 0
_step_start = 0
_active = False
_text = ""


def _text_to_pattern(text):
    """Convierte texto a array de (duracion_en_unidades, led_on)."""
    pat = []
    words = text.upper().split()
    for wi, word in enumerate(words):
        for ci, ch in enumerate(word):
            code = _CODE.get(ch)
            if not code:
                continue
            for si, symbol in enumerate(code):
                # Dot = 1 unit ON, Dash = 3 units ON
                pat.append((1 if symbol == '.' else 3, True))
                # Intra-character gap = 1 unit OFF (except after last symbol)
                if si < len(code) - 1:
                    pat.append((1, False))
            # Inter-character gap = 3 units OFF (except after last char in word)
            if ci < len(word) - 1:
                pat.append((3, False))
        # Inter-word gap = 7 units OFF (except after last word)
        if wi < len(words) - 1:
            pat.append((7, False))
    return pat


def start(text, now_ms):
    """Inicia transmision de morse."""
    global _pattern, _index, _step_start, _active, _text
    _text = text[:_MAX_LEN]
    _pattern = _text_to_pattern(_text)
    _index = 0
    _step_start = now_ms
    _active = bool(_pattern)


def tick(now_ms, led_set_raw_fn, brightness):
    """Avanza un paso. Retorna True si sigue, False si termino."""
    global _index, _step_start, _active

    if not _active or _index >= len(_pattern):
        _active = False
        led_set_raw_fn(0)
        return False

    duration_units, is_on = _pattern[_index]
    duration_ms = duration_units * config.MORSE_UNIT_MS
    elapsed = time.ticks_diff(now_ms, _step_start)

    if is_on:
        led_set_raw_fn(brightness)
    else:
        led_set_raw_fn(0)

    if elapsed >= duration_ms:
        _index += 1
        _step_start = now_ms
        if _index >= len(_pattern):
            _active = False
            led_set_raw_fn(0)
            return False

    return True


def is_active():
    return _active


def get_text():
    return _text if _active else ""
