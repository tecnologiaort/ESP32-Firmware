# -*- coding: utf-8 -*-
"""
Módulo Principal EDA (Fachada Unificada)
Uso recomendado para alumnos: from eda import *
"""
#2026 22-10 Hola

import time
import eda_core
import eda_i2c
import eda_wifi
import eda_bt

# ======================================================================
# --- CONTROL DE ESTADO INTERNO ----------------------------------------
# ======================================================================
_i2c_activo = True
_bt_activo = True
_wifi_activo = True

# ======================================================================
# --- OBJETO "ESPEJO" PARA BLUETOOTH -----------------------------------
# ======================================================================
class _ControlRemotoBT:
    """Combina el envío por canales y la ejecución de funciones remotas."""
    
    # 1. Sistema de Canales (Datos sueltos y Canal Default)
    def enviar(self, arg1, arg2=None):
        """
        Si pasás 2 datos: enviar("canal", valor)
        Si pasás 1 dato: enviar(valor) -> usa el canal "default"
        """
        canal = "default" if arg2 is None else arg1
        valor = arg1 if arg2 is None else arg2
        
        if _bt_activo:
            eda_bt.enviar_canal(canal, valor)

    def leer(self, canal="default", por_defecto=0):
        if _bt_activo:
            return eda_bt.leer_canal(canal, por_defecto)
        return por_defecto
        
    def leerTexto(self, canal="default", por_defecto=""):
        if _bt_activo:
            return eda_bt.leer_texto(canal, por_defecto)
        return por_defecto

    # 2. Sistema RPC (Ejecución remota mágica)
    def __getattr__(self, nombre_funcion):
        def empaquetador(*argumentos):
            if not _bt_activo:
                print(f"Aviso: BT inactivo. No se ejecutó '{nombre_funcion}'")
                return None
                
            funciones_de_lectura = ['entradaDigital', 'entradaAnalogica', 'sensorDistancia', 'leerTeclado']
            esperar = nombre_funcion in funciones_de_lectura
            
            eda_bt.enviar_comando_remoto(nombre_funcion, esperar, *argumentos)
            
            if esperar:
                return eda_bt.esperar_respuesta(timeout_ms=500)
                
        return empaquetador

bt = _ControlRemotoBT()
 
# ======================================================================
# --- OBJETO "ESPEJO" PARA WIFI ----------------------------------------
# ======================================================================
class _ControlRemotoWiFi:
    
    # 1. Sistema de Canales (Soporta canal default y devuelve None si está vacío)
    def enviar(self, arg1, arg2=None):
        canal = "default" if arg2 is None else arg1
        valor = arg1 if arg2 is None else arg2
        if _wifi_activo: 
            eda_wifi.enviar_canal(canal, valor)

    def leer(self, canal="default", por_defecto=None):
        if _wifi_activo: 
            return eda_wifi.leer_canal(canal, por_defecto)
        return por_defecto

    def leerTexto(self, canal="default", por_defecto=None):
        if _wifi_activo: 
            return eda_wifi.leer_texto(canal, por_defecto)
        return por_defecto

    def limpiarBuffer(self):
        """Elimina todos los mensajes y datos recibidos previamente."""
        if _wifi_activo:
            eda_wifi.limpiar_buffer()

    # 2. Sistema RPC (Ejecución remota de funciones)
    def __getattr__(self, nombre_funcion):
        def empaquetador(*argumentos):
            if not _wifi_activo:
                return None
                
            funciones_lectura = ['entradaDigital', 'entradaAnalogica', 'sensorDistancia', 'leerTecladoI2C']
            esperar = nombre_funcion in funciones_lectura
            
            eda_wifi.enviar_comando_remoto(nombre_funcion, esperar, *argumentos)
            
            if esperar:
                return eda_wifi.esperar_respuesta(timeout_ms=500)
                
        return empaquetador

wifi = _ControlRemotoWiFi()

# ======================================================================
# --- FUNCIONES LOCALES DEL ROBOT --------------------------------------
# ======================================================================

def iniciar(placa="N_ESP32", usar_i2c=True, usar_bt=False):
    global _i2c_activo, _bt_activo
    print("\n--- INICIANDO SISTEMA EDA ---")
    eda_core.configurar_placa(placa)
    
    if usar_i2c:
        _i2c_activo = eda_i2c.inicializar_bus(eda_core.PINS['I2C'])
    if usar_bt:
        eda_bt.inicializar_uart()
        _bt_activo = True
    print("-----------------------------\n")
    

# ======================================================================
# --- SENSORIZACIÓN Y ACTUACIÓN BÁSICA (Módulo Core) -------------------
# ======================================================================

def entradaDigital(n_entrada: int) -> int:
    """Lee el estado (0 o 1) de una entrada digital (1 a 4)."""
    return eda_core.leer_entrada_digital(n_entrada)

def entradaAnalogica(n_entrada: int) -> int:
    """Lee el porcentaje (0 a 100%) de una entrada analógica (1 a 4)."""
    return eda_core.leer_entrada_analogica(n_entrada)

def salidaDigital(n_salida: int, estado: bool):
    """Enciende (True) o apaga (False) una salida digital (1 a 4)."""
    eda_core.escribir_salida_digital(n_salida, estado)

def salidaAnalogica(n_salida: int, potencia: int, frecuencia: int = 1000):
    """Controla la potencia (0 a 100%) de una salida mediante PWM (1 a 4)."""
    eda_core.escribir_salida_analogica(n_salida, potencia, frecuencia)
    
def RGB(n_salida: int, brillo: int = 100, r: int = 255, g: int = 255, b: int = 255, n_led: int = 0, qleds: int = 7):
    """Controla una matriz NeoPixel en la salida especificada (1, 2 o 3)."""
    eda_core.controlar_neopixel(n_salida, brillo, r, g, b, n_led, qleds)


# ======================================================================
# --- MOTORES Y SENSORES AVANZADOS (Módulo Core) -----------------------
# ======================================================================

def motorRC(n_salida: int, velocidad: int):
    """Mueve un motor RC (-100 a 100) en la salida seleccionada (1 a 4)."""
    eda_core.escribir_motor_rc(n_salida, velocidad)

def servomotor(n_salida: int, angulo: int):
    """Mueve un servo de rotación acotada (0 a 180 grados) (1 a 4)."""
    eda_core.escribir_servomotor(n_salida, angulo)

def sensorDistancia(n_entrada: int) -> float:
    """Retorna la distancia en centímetros medida por el sensor ultrasónico (1 a 4)."""
    return eda_core.leer_distancia(n_entrada)

def buzzer(n_salida: int, volumen: int = 20, nota: int = 9, octava: int = 4):
    """Reproduce un tono musical en el buzzer asignado a una salida (1 a 4)."""
    eda_core.reproducir_tono(n_salida, volumen, nota, octava)

def mapeo(x: int, cero: int = 33, out_min: int = -100, out_max: int = 100, in_min: int = 0, in_max: int = 100) -> int:
    return int(eda_core.mapeo_joystick(x, cero, out_min, out_max, in_min, in_max))

def detenerTodo():
    """Apaga todos los motores, actuadores y limpia las pantallas."""
    eda_core.apagar_todo()
    if _i2c_activo:
        eda_i2c.limpiar_todo()
    print("Robot completamente detenido de forma segura.")


# ======================================================================
# --- PANTALLA LCD Y TECLADO (Módulo I2C) ------------------------------
# ======================================================================

def printLCD(columna: int, fila: int, texto, direccion: int = None):
    """Escribe texto en una pantalla LCD en la columna y fila indicadas."""
    if _i2c_activo:
        eda_i2c.escribir_lcd(columna, fila, str(texto), direccion)
 
def limpiarLCD(direccion: int = None):
    """Borra el contenido de las pantallas LCD."""
    if _i2c_activo:
        eda_i2c.limpiar_lcd(direccion)

def luzLCD(estado: bool, direccion: int = None):
    """Enciende o apaga la retroiluminación de la pantalla."""
    if _i2c_activo:
        eda_i2c.controlar_luz(estado, direccion)

def leerTeclado(id_teclado: int = None) -> str:
    """Retorna la tecla pulsada en el teclado matricial o None si no hay pulsación."""
    if _i2c_activo:
        return eda_i2c.leer_tecla(id_teclado)
    return None

# ======================================================================
# --- PANTALLA OLED ----------------------------------------------------
# ======================================================================

def printOLED(columna: int, fila: int, texto, escala: int = 1):
    """Escribe texto en el OLED en coordenadas de caracteres (8x8 px)."""
    if _i2c_activo: eda_i2c.oled_print(columna, fila, texto, escala)

def mostrarOLED():
    """Vuelca los gráficos o textos a la pantalla física OLED."""
    if _i2c_activo: eda_i2c.oled_mostrar()

def limpiarOLED():
    """Borra toda la pantalla OLED."""
    if _i2c_activo: eda_i2c.oled_limpiar()

def luzOLED(estado: bool):
    """Enciende (True) o apaga (False) el display OLED."""
    if _i2c_activo: eda_i2c.oled_luz(estado)

def invertirOLED(estado: bool):
    """Invierte los colores del OLED."""
    if _i2c_activo: eda_i2c.oled_invertir(estado)

def contrasteOLED(valor: int):
    """Ajusta el contraste del OLED (0-255)."""
    if _i2c_activo: eda_i2c.oled_contraste(valor)

def pixelOLED(x: int, y: int, color: int = 1):
    """Dibuja un píxel individual."""
    if _i2c_activo: eda_i2c.oled_pixel(x, y, color)

def lineaOLED(x0: int, y0: int, x1: int, y1: int):
    """Dibuja una línea en píxeles."""
    if _i2c_activo: eda_i2c.oled_linea(x0, y0, x1, y1)

def circuloOLED(cx: int, cy: int, radio: int):
    """Dibuja un círculo vacío."""
    if _i2c_activo: eda_i2c.oled_circulo(cx, cy, radio)

def rectOLED(x: int, y: int, ancho: int, alto: int, relleno: bool = False):
    """Dibuja un rectángulo (vacío o relleno)."""
    if _i2c_activo: eda_i2c.oled_rect(x, y, ancho, alto, relleno)

def dibujarOLED(tipo_grafico, titulo: str, v1=None, v2=None, v3=None, v4=None):
    """Genera gráficos automáticos (sismógrafo, vúmetro, tanque, ecualizador, etc)."""
    if _i2c_activo: eda_i2c.orquestar_grafico(tipo_grafico, titulo, v1, v2, v3, v4)

# ======================================================================
# --- COMUNICACIÓN BLUETOOTH (Módulo BT) -------------------------------
# ======================================================================

def btEnviar(mensaje: str):
    """Envía un mensaje de texto a través del módulo Bluetooth."""
    if _bt_activo:
        eda_bt.enviar_datos(mensaje)

def btLeer() -> str:
    """Lee los datos recibidos por Bluetooth. Retorna None si no hay datos."""
    if _bt_activo:
        return eda_bt.leer_datos()
    return None

def btConfigurar(es_maestro: bool, pin_clave: int) -> bool:
    """Configura el rol y la clave del módulo HC-05."""
    return eda_bt.configurar_modulo(es_maestro, pin_clave)

def escucharBluetooth():
    if not _bt_activo: return
        
    paquete = eda_bt.leer_puerto_remoto()
    if paquete:
        nombre_comando = paquete["f"]
        argumentos = paquete["a"] # Esto es una lista, por ejemplo: [1, 1]
        requiere_respuesta = paquete.get("req", False)
        
        if nombre_comando in globals() and callable(globals()[nombre_comando]):
            funcion_local = globals()[nombre_comando]
            try:
                # ¡ACÁ ESTÁ EL OTRO SOSPECHOSO!
                # Si dice 'funcion_local(argumentos)', pasa la lista entera como 1 solo parámetro.
                # DEBE decir 'funcion_local(*argumentos)' para que los separe.
                resultado = funcion_local(*argumentos)
                
                if requiere_respuesta:
                    eda_bt.enviar_respuesta(resultado)
                    
            except Exception as e:
                print(f"Error ejecutando '{nombre_comando}' remotamente: {e}")


# ======================================================================
# --- WIFI -------------------------
# ======================================================================

def iniciarAP(ssid="EDA_Red", password="eda12345", canal=6):
    global _wifi_activo
    _wifi_activo = eda_wifi.iniciar_ap(ssid, password, canal)

def iniciarSTA(ssid="EDA_Red", password="eda12345"):
    global _wifi_activo
    _wifi_activo = eda_wifi.iniciar_sta(ssid, password)
 
def escucharWifi():

    # --- ESCUCHA WIFI ---
    if _wifi_activo:
        paquete_wf = eda_wifi.leer_puerto_remoto()
        if paquete_wf:
            _ejecutar_paquete(paquete_wf, eda_wifi)

def _ejecutar_paquete(paquete, modulo_red):
    """Función interna que procesa el JSON recibido y activa los motores/sensores."""
    nombre_comando = paquete["f"]
    argumentos = paquete["a"]
    requiere_respuesta = paquete.get("req", False)
    
    if nombre_comando in globals() and callable(globals()[nombre_comando]):
        funcion_local = globals()[nombre_comando]
        try:
            resultado = funcion_local(*argumentos)
            if requiere_respuesta:
                modulo_red.enviar_respuesta(resultado)
        except Exception as e:
            print(f"Error remoto '{nombre_comando}': {e}")


time.sleep(0.2)
iniciar(placa=modelo)
