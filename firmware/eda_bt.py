# -*- coding: utf-8 -*-
"""
Módulo Interno Bluetooth (eda_bt.py)
Gestiona la comunicación UART y el empaquetado de comandos remotos (JSON).
"""

from machine import UART
import utime
import json

# ======================================================================
# --- 1. CONFIGURACIÓN DEL HARDWARE ------------------------------------
# ======================================================================

BAUDIOS = 115200
uart = UART(1, baudrate=BAUDIOS)

def inicializar_uart(tx_pin=17, rx_pin=16):
    """Inicializa el puerto serie para comunicarse con el HC-05."""
    global uart
    try:
        # El ESP32 usa típicamente UART 2 para periféricos externos
        uart = UART(1, baudrate=BAUDIOS, tx=tx_pin, rx=rx_pin)
        print("BT: UART2 inicializada correctamente.")
        return True
    except Exception as e:
        print(f"Error crítico al inicializar Bluetooth: {e}")
        return False


# ======================================================================
# --- 2. CONFIGURACIÓN DEL MÓDULO (COMANDOS AT) ------------------------
# ======================================================================

def _enviar_comando_at(comando: str) -> bool:
    """Envía un comando AT al HC-05 a 38400 baudios (modo configuración)."""
    global uart
    
    # 1. Apagamos el UART solo si ya estaba encendido previamente
    if uart is not None:
        uart.deinit()
        
    # 2. Iniciamos en modo configuración (38400)
    uart = UART(1, baudrate=38400)
    
    # Limpiamos basura del buffer si la hubiera (try/except por seguridad en ESP32)
    try:
        uart.read() 
    except:
        pass
        
    # 3. Enviamos el comando
    uart.write(comando + '\r\n')
    utime.sleep(1)   
    respuesta = uart.read()
    
    # 4. Volvemos a apagar y restauramos la velocidad normal (115200)
    if uart is not None:
        uart.deinit()
    uart = UART(1, baudrate=BAUDIOS)
    
    # 5. Evaluamos la respuesta
    if respuesta is None:
        return False
    return len(respuesta) < 20

def configurar_modulo(es_maestro: bool, clave: int) -> bool:
    """Configura el rol, nombre y clave del HC-05."""
    print("Configurando el modulo BT...")
    if not (1000 <= clave <= 9999):
        print("BT Error: La clave debe tener 4 dígitos (ej: 1234).")
        return False
        
    rol = 1 if es_maestro else 0
    nombre = f"BT_{'MAESTRO' if es_maestro else 'ESCLAVO'}_{clave}"
    
    if _enviar_comando_at('AT'):
        _enviar_comando_at(f"AT+ROLE={rol}")
        _enviar_comando_at(f"AT+CMODE={1 if es_maestro else 0}")
        _enviar_comando_at(f"AT+NAME={nombre}")
        _enviar_comando_at(f"AT+UART={BAUDIOS},0,0")
        _enviar_comando_at(f"AT+PSWD=\"{clave}\"")
        _enviar_comando_at("AT+RESET")
     
        print(f"Configuracion Exitosa. \nClave: {clave}\nBaudrate: {BAUDIOS}\nModo: {'Maestro' if es_maestro else 'Esclavo'}")
        return True
        
    print("BT Error: El HC-05 no está en modo AT. Desconecte, mantenga el botón pulsado y conecte de nuevo.")
    return False
  

# ======================================================================
# --- 3. PROTOCOLO JSON (RPC Y CANALES) --------------------------------
# ======================================================================

# Diccionarios de memoria para el sistema de canales
_datos_rx = {}  
_textos_rx = {} 

def _procesar_entrada():
    """
    Lee UART constantemente. Si es un canal, lo guarda en los diccionarios.
    Si es un comando RPC ("f") o respuesta ("res"), lo devuelve a la fachada.
    """
    if not uart: return None
    
    while uart.any():
        try:
            linea = uart.readline()
            if not linea: continue
            texto = linea.decode('utf-8').strip()
             
            # --- INTENTAMOS LEER COMO JSON OFICIAL ---
            try:
                paquete = json.loads(texto)
                
                if "c" in paquete:
                    if paquete.get("t") == "s":
                        _textos_rx[paquete["c"]] = paquete.get("v", "")
                    else:
                        _datos_rx[paquete["c"]] = float(paquete.get("v", 0.0))
                elif "f" in paquete or "res" in paquete:
                    return paquete
            
            # --- ¡MAGIA! SI NO ES JSON, ES TEXTO PLANO DEL CELULAR ---
            except ValueError:
                if texto:
                    try:
                        # Si el alumno tipeó un número (ej: "100"), va a datos numéricos
                        _datos_rx["default"] = float(texto)
                    except ValueError:
                        # Si el alumno tipeó palabras (ej: "Hola"), va a textos
                        _textos_rx["default"] = texto
                        
        except Exception:
            pass
            
    return None

def enviar_comando_remoto(nombre_funcion, requiere_respuesta, *args):
    if not uart: return
    trama = {"f": nombre_funcion, "req": requiere_respuesta, "a": args}
    try:
        uart.write(json.dumps(trama) + '\n')
    except: pass

def enviar_datos(valor):
    if not uart: return
    trama = {"res": valor}
    try:
        uart.write(json.dumps(trama) + '\n')
    except: pass

def leer_datos(timeout_ms=500):
    if uart and uart.any():
        try:
            linea = uart.readline().decode('utf-8').strip()
            
            if not linea:
                return None
            
            # 1. Intentamos ver si el mensaje tiene el envoltorio JSON de nuestra librería
            try:
                paquete = _procesar_entrada()
                if "res" in paquete:
                    # Le sacamos el envoltorio y devolvemos solo el valor (ej: "HOLA 58")
                    return str(paquete["res"])
            except ValueError:
                # 2. Si falla json.loads, significa que no era JSON. 
                # Es un texto plano común enviado con btEnviar(). Lo devolvemos tal cual.
                return linea
                
        except Exception:
            pass
            
    return None
 
def leer_puerto_remoto() -> dict:
    """Lee comandos entrantes. Ignora las respuestas (ya manejadas por esperar_respuesta)."""
    if uart and uart.any():
        try:
            linea = uart.readline().decode('utf-8').strip()
            paquete = _procesar_entrada()
            # Solo devolvemos si es una orden ("f")
            if "f" in paquete and "a" in paquete:
                return paquete
        except:
            pass
    return None

def enviar_canal(canal: str, valor):
    if not uart: return
    t = "s" if isinstance(valor, str) else "n"
    trama = {"c": canal, "t": t, "v": valor}
    try:
        uart.write(json.dumps(trama) + '\n')
    except: pass

def leer_canal(canal: str, por_defecto=0):
    _procesar_entrada() # Vaciamos el buffer para tener el último valor
    return int(round(_datos_rx.get(canal, por_defecto)))

def leer_texto(canal: str, por_defecto=""):
    _procesar_entrada()
    return _textos_rx.get(canal, por_defecto)