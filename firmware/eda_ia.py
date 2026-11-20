# -*- coding: utf-8 -*-
"""
Módulo eda_ia.py  --  CORRE EN LA ESP32 (MicroPython)

Recibe por el USB la predicción que manda la notebook (clasificador_pc.py)
y se la entrega al programa del alumno con leerPrediccion().

Si deja de llegar una predicción confiable, apaga las salidas digitales
para que los LEDs no queden "pegados" en el último estado.
"""

import sys
import select
import utime
import eda_core

_entrada = select.poll()
_entrada.register(sys.stdin, select.POLLIN)

_ultimo_dato = utime.ticks_ms()   # momento de la última predicción confiable
_ultima_clase = None              # para avisar solo cuando cambia
_apagado = False                  # evita apagar las salidas una y otra vez


def _apagar_salidas():
    for n in range(1, 5):
        eda_core.escribir_salida_digital(n, False)


def leer_prediccion(umbral=85, espera=1000, apagar=True):
    """Devuelve el número de clase que detectó la notebook, o None.

    umbral: confianza mínima, de 0 a 100 (%). Si la notebook está menos
            segura que eso, o no llegó nada nuevo, devuelve None.
    espera: milisegundos sin una predicción confiable antes de apagar
            las salidas digitales 1 a 4.
    apagar: poner False para que NO apague las salidas."""
    global _ultimo_dato, _ultima_clase, _apagado

    clase = _leer_clase(umbral)

    if clase is None:
        if apagar and not _apagado and utime.ticks_diff(utime.ticks_ms(), _ultimo_dato) > espera:
            _apagar_salidas()
            _apagado = True
            _ultima_clase = None
        return None

    _ultimo_dato = utime.ticks_ms()
    _apagado = False
    if clase != _ultima_clase:
        _ultima_clase = clase
        print("Recibi clase:", clase)
    return clase


leerPrediccion = leer_prediccion   # mismo nombre que en ORT, por si se usa eda_ia directo


def _leer_clase(umbral):
    if not _entrada.poll(50):
        return None
    linea = sys.stdin.readline()
    while _entrada.poll(0):            # si hay varias en espera, vale la última
        otra = sys.stdin.readline()
        if not otra:                   # no quedó nada para leer
            break
        linea = otra
    try:
        partes = linea.strip().split(",")
        clase = int(partes[0])
        confianza = int(partes[1])
    except (ValueError, IndexError):
        return None
    if confianza >= umbral:
        return clase
    return None
