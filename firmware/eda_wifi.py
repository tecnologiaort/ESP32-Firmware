# -*- coding: utf-8 -*-
"""
Módulo Interno WiFi (eda_wifi.py) - Versión Optimizada y Extendida
Gestiona comunicación UDP local (Canales y RPC), estado de red, hora/fecha NTP
y peticiones HTTP/JSON seguras para la RAM del ESP32.
"""

import network
import socket
import json
import utime
import gc

# ======================================================================
# --- CONFIGURACIÓN Y ESTADO -------------------------------------------
# ======================================================================

_PORT = 4210
_IP_AP = "192.168.4.1"
_MAX_COLA_RPC = 20

_modo = None
_wlan = None
_sock = None
_ip_destino = None
_iniciado = False
_hora_sincronizada = False

_datos_rx = {}
_textos_rx = {}
_cola_rpc = []

# ======================================================================
# --- 1. INICIALIZACIÓN, DESCONEXIÓN Y ESCANEO -------------------------
# ======================================================================

def _cerrar_socket():
    """Cierra el socket UDP actual para evitar fugas de RAM."""
    global _sock, _iniciado
    if _sock:
        try:
            _sock.close()
        except OSError:
            pass
        _sock = None
    _iniciado = False

def _crear_socket_udp():
    """Crea un único socket UDP no bloqueante."""
    global _sock
    _cerrar_socket()
    _sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    _sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    _sock.bind(("0.0.0.0", _PORT))
    _sock.setblocking(False)

def iniciar_ap(ssid="EDA_Red", password="eda12345", canal=6) -> bool:
    global _wlan, _modo, _ip_destino, _iniciado
    print(f"WiFi: Iniciando Access Point '{ssid}'...")

    _wlan = network.WLAN(network.AP_IF)
    _wlan.active(True)
    _wlan.config(essid=ssid, password=password, authmode=3, channel=canal)

    t0 = utime.ticks_ms()
    while not _wlan.active():
        if utime.ticks_diff(utime.ticks_ms(), t0) > 3000:
            print("WiFi Error: No se pudo activar el AP.")
            return False
        utime.sleep_ms(100)

    _modo = "AP"
    _ip_destino = None
    _crear_socket_udp()
    _iniciado = True
    gc.collect()

    print(f"WiFi: AP Activo (IP: {ipWifi()}) - Esperando conexión...")
    return True

def iniciar_sta(ssid="EDA_Red", password="eda12345", timeout=10) -> bool:
    global _wlan, _modo, _ip_destino, _iniciado, _hora_sincronizada
    print(f"WiFi: Conectando a '{ssid}'...")

    _wlan = network.WLAN(network.STA_IF)
    _wlan.active(True)
    if not _wlan.isconnected():
        _wlan.connect(ssid, password)

    t0 = utime.ticks_ms()
    intentos = 0
    while not _wlan.isconnected():
        if utime.ticks_diff(utime.ticks_ms(), t0) > timeout * 1000:
            print("WiFi Error: Tiempo de espera agotado.")
            return False
        if intentos % 5 == 0:
            print("WiFi: Conectando...")
        utime.sleep_ms(300)
        intentos += 1

    _modo = "STA"
    _ip_destino = _IP_AP
    _hora_sincronizada = False
    _crear_socket_udp()
    _iniciado = True
    gc.collect()

    print(f"WiFi: Conectado (IP Propia: {ipWifi()})")

    utime.sleep_ms(200)
    _enviar_raw({"c": "__hello__", "t": "s", "v": "STA"})
    return True

def desconectarWifi():
    """Cierra el socket, desconecta la red y apaga la radio WiFi para ahorrar RAM y energía."""
    global _wlan, _modo, _ip_destino, _hora_sincronizada
    _cerrar_socket()
    if _wlan:
        try:
            if _modo == "STA" and _wlan.isconnected():
                _wlan.disconnect()
            _wlan.active(False)
        except Exception:
            pass
    _wlan = None
    _modo = None
    _ip_destino = None
    _hora_sincronizada = False
    gc.collect()
    print("WiFi: Desconectado y apagado.")

def escanearRedes() -> list:
    """
    Escanea redes WiFi cercanas y devuelve una lista de tuplas (SSID, señal_dBm)
    ordenadas de mayor a menor intensidad de señal.
    """
    sta = network.WLAN(network.STA_IF)
    estaba_activo = sta.active()
    if not estaba_activo:
        sta.active(True)

    redes = []
    try:
        encontradas = sta.scan()
        for red in encontradas:
            ssid = red[0].decode("utf-8", "ignore").strip()
            rssi = red[3]
            if ssid:
                redes.append((ssid, rssi))
        redes.sort(key=lambda x: x[1], reverse=True)
    except Exception as e:
        print(f"WiFi Error escaneando: {e}")
    finally:
        if not estaba_activo:
            sta.active(False)
        gc.collect()

    return redes

# ======================================================================
# --- 2. ESTADO DE RED, HORA Y FECHA (NTP) -----------------------------
# ======================================================================

def estadoWifi() -> bool:
    """Devuelve True si está conectado a una red (STA) o si el AP está activo."""
    if _wlan is None:
        return False
    if _modo == "STA":
        return _wlan.isconnected()
    if _modo == "AP":
        return _wlan.active()
    return False

def nombreRed():
    """Devuelve el SSID de la red actual o None si no está conectado."""
    if not estadoWifi():
        return None
    try:
        ssid = _wlan.config("essid")
        return ssid.decode("utf-8") if isinstance(ssid, bytes) else ssid
    except Exception:
        return None

def intensidadWifi():
    """Devuelve la intensidad de la señal en dBm (ej. -65) o None si no aplica."""
    if _modo == "STA" and estadoWifi():
        try:
            return _wlan.status("rssi")
        except Exception:
            return None
    return None

def ipWifi():
    """Devuelve la IP asignada por la red o None si no está conectado."""
    if not estadoWifi():
        return None
    try:
        return _wlan.ifconfig()[0]
    except Exception:
        return None

def _sincronizar_ntp() -> bool:
    """Sincroniza el reloj interno del ESP32 con internet (una sola vez)."""
    global _hora_sincronizada
    if _modo != "STA" or not estadoWifi():
        return False
    gc.collect()
    try:
        import ntptime
        ntptime.settime()
        _hora_sincronizada = True
        return True
    except Exception as e:
        print(f"WiFi NTP Error: {e}")
        return False

def horaActual(gmt=-3, formato="texto"):
    """
    Devuelve la hora actual ajustada a GMT (por defecto GMT-3).
    Opciones de 'formato': "texto" ("14:05:09"), "tupla" (14, 5, 9), "hora", "minuto", "segundo".
    """
    if not _hora_sincronizada:
        if not _sincronizar_ntp():
            return None

    t = utime.localtime(utime.time() + (gmt * 3600))
    h, m, s = t[3], t[4], t[5]

    if formato == "tupla":
        return (h, m, s)
    elif formato == "hora":
        return h
    elif formato == "minuto":
        return m
    elif formato == "segundo":
        return s
    return f"{h:02d}:{m:02d}:{s:02d}"

def fechaActual(gmt=-3, formato="texto"):
    """
    Devuelve la fecha actual ajustada a GMT (por defecto GMT-3).
    Opciones de 'formato': "texto" ("24/11/2026"), "tupla" (2026, 11, 24), "dia", "mes", "año".
    """
    if not _hora_sincronizada:
        if not _sincronizar_ntp():
            return None

    t = utime.localtime(utime.time() + (gmt * 3600))
    anio, mes, dia = t[0], t[1], t[2]

    if formato == "tupla":
        return (anio, mes, dia)
    elif formato == "dia":
        return dia
    elif formato == "mes":
        return mes
    elif formato == "año":
        return anio
    return f"{dia:02d}/{mes:02d}/{anio}"

# ======================================================================
# --- 3. PETICIONES WEB (HTTP / JSON / POST) ---------------------------
# ======================================================================

def descargarWeb(url: str, max_bytes: int = 2048, timeout: int = 5):
    """
    Descarga contenido de una URL limitando la lectura a 'max_bytes' para evitar MemoryError.
    """
    if _modo != "STA" or not estadoWifi():
        print("WiFi Error: Necesitás conexión a internet en modo STA.")
        return None

    gc.collect()
    resp = None
    try:
        import urequests
        resp = urequests.get(url, timeout=timeout)
        if resp.status_code == 200:
            datos_crudos = resp.raw.read(max_bytes)
            try:
                return datos_crudos.decode("utf-8")
            except UnicodeError:
                return str(datos_crudos)
        else:
            print(f"WiFi HTTP Error: Código {resp.status_code}")
            return None
    except Exception as e:
        print(f"WiFi Error descargando web: {e}")
        return None
    finally:
        if resp:
            resp.close()
        gc.collect()

def descargarJSON(url: str, max_bytes: int = 4096, timeout: int = 5):
    """
    Descarga una API en formato JSON y la devuelve como diccionario o lista de Python.
    """
    texto = descargarWeb(url, max_bytes=max_bytes, timeout=timeout)
    if texto is None:
        return None
    try:
        return json.loads(texto)
    except ValueError as e:
        print(f"WiFi Error JSON (puede haberse truncado por max_bytes): {e}")
        return None
    finally:
        gc.collect()

def enviarDatoWeb(url: str, datos, timeout: int = 5) -> bool:
    """
    Envía datos mediante HTTP POST a una URL (Webhook, Google Sheets, Telegram, etc.).
    Si 'datos' es un diccionario o lista, se envía como JSON. Devuelve True si fue exitoso.
    """
    if _modo != "STA" or not estadoWifi():
        print("WiFi Error: Necesitás conexión a internet en modo STA.")
        return False

    gc.collect()
    resp = None
    try:
        import urequests
        if isinstance(datos, (dict, list)):
            resp = urequests.post(url, json=datos, timeout=timeout)
        else:
            resp = urequests.post(url, data=str(datos), timeout=timeout)

        exito = 200 <= resp.status_code < 300
        if not exito:
            print(f"WiFi POST Error: Código {resp.status_code}")
        return exito
    except Exception as e:
        print(f"WiFi Error enviando dato web: {e}")
        return False
    finally:
        if resp:
            resp.close()
        gc.collect()

# ======================================================================
# --- 4. MOTOR UDP INTELIGENTE (LECTURA Y ESCRITURA) -------------------
# ======================================================================

def _leer_socket():
    """Lee el buffer físico UDP, guarda variables y encola comandos RPC."""
    global _ip_destino
    if not _iniciado or not _sock:
        return

    try:
        while True:
            try:
                data, addr = _sock.recvfrom(512)
            except OSError:
                break

            texto = data.decode("utf-8").strip()

            if _modo == "AP" and _ip_destino is None:
                _ip_destino = addr[0]
                print(f"WiFi: Station vinculado en IP {_ip_destino}")

            try:
                paquete = json.loads(texto)

                if isinstance(paquete, dict):
                    if "c" in paquete:
                        if paquete["c"] != "__hello__":
                            if paquete.get("t") == "s":
                                _textos_rx[paquete["c"]] = str(paquete.get("v", ""))
                            else:
                                try:
                                    _datos_rx[paquete["c"]] = float(paquete.get("v", 0.0))
                                except (ValueError, TypeError):
                                    pass

                    elif "f" in paquete or "res" in paquete:
                        if len(_cola_rpc) >= _MAX_COLA_RPC:
                            _cola_rpc.pop(0)
                        _cola_rpc.append(paquete)
                else:
                    raise ValueError()

            except ValueError:
                if texto:
                    try:
                        _datos_rx["default"] = float(texto)
                    except ValueError:
                        _textos_rx["default"] = texto

    except Exception as e:
        print(f"WiFi Error Lector: {e}")

def _enviar_raw(diccionario: dict) -> bool:
    """Envía un diccionario JSON al otro ESP32."""
    _leer_socket()

    if not _iniciado or _ip_destino is None or not _sock:
        return False

    try:
        _sock.sendto(json.dumps(diccionario).encode("utf-8"), (_ip_destino, _PORT))
        return True
    except Exception:
        return False

# ======================================================================
# --- 5. FUNCIONES PARA LA FACHADA (RPC Y CANALES) ---------------------
# ======================================================================

def enviar_comando_remoto(nombre_funcion, requiere_respuesta, *args):
    _enviar_raw({"f": nombre_funcion, "req": requiere_respuesta, "a": args})

def enviar_respuesta(valor):
    _enviar_raw({"res": valor})

def esperar_respuesta(timeout_ms=500):
    t0 = utime.ticks_ms()
    while utime.ticks_diff(utime.ticks_ms(), t0) < timeout_ms:
        _leer_socket()
        for i, pkt in enumerate(_cola_rpc):
            if "res" in pkt:
                return _cola_rpc.pop(i)["res"]
        utime.sleep_ms(10)

    print("WiFi Aviso: Tiempo de respuesta agotado.")
    return None

def leer_puerto_remoto():
    """Entrega el comando ('f') más antiguo de la cola a la Fachada."""
    _leer_socket()
    for i, pkt in enumerate(_cola_rpc):
        if "f" in pkt:
            return _cola_rpc.pop(i)
    return None

def enviar_canal(canal: str, valor):
    t = "s" if isinstance(valor, str) else "n"
    _enviar_raw({"c": canal, "t": t, "v": valor})

def leer_canal(canal: str, por_defecto=None):
    _leer_socket()
    valor = _datos_rx.get(canal, por_defecto)
    if valor is None:
        return None
    try:
        return int(round(valor))
    except Exception:
        return por_defecto

def leer_texto(canal: str, por_defecto=None):
    _leer_socket()
    return _textos_rx.get(canal, por_defecto)

def buscarCanales() -> list:
    """
    Devuelve una lista con los nombres de todos los canales (numéricos y de texto)
    que hayan enviado datos hasta el momento.
    """
    _leer_socket()
    canales = set(_datos_rx.keys())
    canales.update(_textos_rx.keys())
    return list(canales)

def limpiar_buffer():
    """Vacía diccionarios, cola RPC y buffer físico UDP."""
    _datos_rx.clear()
    _textos_rx.clear()
    _cola_rpc.clear()

    if _sock:
        try:
            while True:
                _sock.recvfrom(512)
        except OSError:
            pass
    gc.collect()
