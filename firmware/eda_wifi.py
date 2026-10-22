# -*- coding: utf-8 -*-
"""
Módulo Interno WiFi (eda_wifi.py)
Gestiona la comunicación UDP en red local con Cola de Mensajes Anti-Pérdida.
Soporta canales clásicos, envío de variables sueltas y comandos remotos (RPC).
"""

import network
import socket
import json
import utime

# ======================================================================
# --- CONFIGURACIÓN Y ESTADO -------------------------------------------
# ======================================================================

_PORT = 4210
_IP_AP = "192.168.4.1"

_modo = None
_wlan = None
_sock_envio = None
_sock_recibo = None
_ip_destino = None
_iniciado = False

_datos_rx = {}  
_textos_rx = {} 
_cola_rpc = []  # <--- NUEVO: Sala de espera para comandos remotos

# ======================================================================
# --- 1. INICIALIZACIÓN (AP y STA) -------------------------------------
# ======================================================================

def iniciar_ap(ssid="EDA_Red", password="eda12345", canal=6) -> bool:
    global _wlan, _modo, _sock_envio, _sock_recibo, _ip_destino, _iniciado
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

    _sock_recibo = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    _sock_recibo.bind(("0.0.0.0", _PORT))
    _sock_recibo.setblocking(False)

    _sock_envio = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    _sock_envio.setblocking(False)

    _iniciado = True
    print(f"WiFi: AP Activo (IP: {_wlan.ifconfig()[0]}) - Esperando conexión...")
    return True

def iniciar_sta(ssid="EDA_Red", password="eda12345", timeout=10) -> bool:
    global _wlan, _modo, _sock_envio, _sock_recibo, _ip_destino, _iniciado
    print(f"WiFi: Conectando a '{ssid}'...")

    _wlan = network.WLAN(network.STA_IF)
    _wlan.active(True)
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

    _sock_recibo = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    _sock_recibo.bind(("0.0.0.0", _PORT))
    _sock_recibo.setblocking(False)

    _sock_envio = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    _sock_envio.setblocking(False)

    _iniciado = True
    print(f"WiFi: Conectado (IP Propia: {_wlan.ifconfig()[0]})")

    # Handshake para que el AP nos detecte al instante
    utime.sleep_ms(200)
    _enviar_raw({"c": "__hello__", "t": "s", "v": "STA"})
    return True

# ======================================================================
# --- 2. MOTOR UDP INTELIGENTE (LECTURA Y ESCRITURA) -------------------
# ======================================================================

def _leer_socket():
    """Lee el buffer físico UDP, guarda variables y encola comandos RPC."""
    global _ip_destino, _cola_rpc
    if not _iniciado or not _sock_recibo:
        return

    try:
        while True:
            try:
                data, addr = _sock_recibo.recvfrom(512)
            except OSError:
                break # El buffer está vacío, terminamos de leer
                
            texto = data.decode('utf-8').strip()

            # El Access Point aprende la IP de forma automática
            if _modo == "AP" and _ip_destino is None:
                _ip_destino = addr[0]
                print(f"WiFi: Station vinculado en IP {_ip_destino}")

            try:
                paquete = json.loads(texto)
                
                # Validación estricta para evitar TypeErrors si mandan un número suelto
                if isinstance(paquete, dict):
                    # --- 1. Es un dato de un Canal ---
                    if "c" in paquete:
                        if paquete["c"] != "__hello__":
                            if paquete.get("t") == "s":
                                _textos_rx[paquete["c"]] = str(paquete.get("v", ""))
                            else:
                                try:
                                    _datos_rx[paquete["c"]] = float(paquete.get("v", 0.0))
                                except (ValueError, TypeError):
                                    pass
                    
                    # --- 2. Es un Comando Remoto (RPC) -> Va a la sala de espera ---
                    elif "f" in paquete or "res" in paquete:
                        _cola_rpc.append(paquete)
                else:
                    raise ValueError() # Forzamos a procesarlo como texto plano

            except ValueError:
                # Textos o números enviados directamente desde una App del celular
                if texto:
                    try:
                        _datos_rx["default"] = float(texto)
                    except ValueError:
                        _textos_rx["default"] = texto

    except Exception as e:
        print(f"WiFi Error Lector: {e}")


def _enviar_raw(diccionario: dict) -> bool:
    """Envía un diccionario JSON al otro ESP32."""
    
    # ¡VITAL! Forzamos leer el puerto antes de enviar. 
    # Esto garantiza que el Handshake sea procesado y se asigne _ip_destino.
    _leer_socket() 
    
    if not _iniciado or _ip_destino is None:
        return False 
        
    try:
        _sock_envio.sendto(json.dumps(diccionario).encode('utf-8'), (_ip_destino, _PORT))
        return True
    except Exception as e:
        # Errores ignorados silenciosamente para no detener el robot
        return False

# ======================================================================
# --- 3. FUNCIONES PARA LA FACHADA (RPC Y CANALES) ---------------------
# ======================================================================

# --- Funciones RPC ---
def enviar_comando_remoto(nombre_funcion, requiere_respuesta, *args):
    _enviar_raw({"f": nombre_funcion, "req": requiere_respuesta, "a": args})

def enviar_respuesta(valor):
    _enviar_raw({"res": valor})

def esperar_respuesta(timeout_ms=500):
    """Espera una respuesta específica buscando en la cola de tareas."""
    t0 = utime.ticks_ms()
    while utime.ticks_diff(utime.ticks_ms(), t0) < timeout_ms:
        _leer_socket()
        
        # Buscamos en la sala de espera si llegó nuestra respuesta
        for i, pkt in enumerate(_cola_rpc):
            if "res" in pkt:
                return _cola_rpc.pop(i)["res"] # La extraemos de la cola
                
        utime.sleep_ms(10)
    
    print("WiFi Aviso: Tiempo de respuesta agotado.")
    return None

def leer_puerto_remoto():
    """Entrega el comando más antiguo de la cola a la Fachada."""
    _leer_socket()
    if _cola_rpc:
        return _cola_rpc.pop(0) # FIFO (First In, First Out)
    return None

# --- Funciones de Canales ---
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
    except:
        return por_defecto

def leer_texto(canal: str, por_defecto=None):
    _leer_socket()
    return _textos_rx.get(canal, por_defecto)

def limpiar_buffer():
    """Vacía los diccionarios, la cola de tareas y el buffer físico UDP."""
    global _datos_rx, _textos_rx, _cola_rpc
    _datos_rx.clear()
    _textos_rx.clear()
    _cola_rpc.clear()
    
    # Vaciamos la memoria del chip de red para que no queden paquetes fantasmas
    if _sock_recibo:
        try:
            while True:
                _sock_recibo.recvfrom(512)
        except OSError:
            pass # Buffer físico vacío