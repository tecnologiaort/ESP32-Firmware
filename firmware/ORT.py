# -*- coding: utf-8 -*-
"""
Módulo Principal EDA (Fachada Unificada)
Uso recomendado para alumnos: from ORT import *
"""

import time
import eda_core

# ======================================================================
# --- CARGA DIFERIDA DE MÓDULOS (LAZY LOADING) -------------------------
# ======================================================================
_eda_i2c = None
_eda_wifi = None
_eda_bt = None
_eda_ia = None

def _i2c():
    global _eda_i2c
    if _eda_i2c is None:
        import eda_i2c
        _eda_i2c = eda_i2c
    return _eda_i2c

def _wifi():
    global _eda_wifi
    if _eda_wifi is None:
        import eda_wifi
        _eda_wifi = eda_wifi
    return _eda_wifi

def _bt():
    global _eda_bt
    if _eda_bt is None:
        import eda_bt
        _eda_bt = eda_bt
    return _eda_bt

def _ia():
    global _eda_ia
    if _eda_ia is None:
        import eda_ia
        _eda_ia = eda_ia
    return _eda_ia

# ======================================================================
# --- CONTROL DE ESTADO INTERNO ----------------------------------------
# ======================================================================
_i2c_activo = False
_bt_activo = False
_wifi_activo = False

# ======================================================================
# --- OBJETO "ESPEJO" PARA BLUETOOTH -----------------------------------
# ======================================================================
class _ControlRemotoBT:
    """Combina el envío por canales y la ejecución de funciones remotas."""

    def enviar(self, arg1, arg2=None):
        canal = "default" if arg2 is None else arg1
        valor = arg1 if arg2 is None else arg2
        if _bt_activo:
            _bt().enviar_canal(canal, valor)

    def leer(self, canal="default", por_defecto=0):
        if _bt_activo:
            return _bt().leer_canal(canal, por_defecto)
        return por_defecto

    def leerTexto(self, canal="default", por_defecto=""):
        if _bt_activo:
            return _bt().leer_texto(canal, por_defecto)
        return por_defecto

    def __getattr__(self, nombre_funcion):
        def empaquetador(*argumentos):
            if not _bt_activo:
                print(f"Aviso: BT inactivo. No se ejecutó '{nombre_funcion}'")
                return None

            funciones_de_lectura = ['entradaDigital', 'entradaAnalogica', 'sensorDistancia', 'sensorPeso', 'leerTeclado']
            esperar = nombre_funcion in funciones_de_lectura

            _bt().enviar_comando_remoto(nombre_funcion, esperar, *argumentos)

            if esperar:
                return _bt().esperar_respuesta(timeout_ms=500)

        return empaquetador

bt = _ControlRemotoBT()

# ======================================================================
# --- OBJETO "ESPEJO" PARA WIFI ----------------------------------------
# ======================================================================
class _ControlRemotoWiFi:

    def enviar(self, arg1, arg2=None):
        canal = "default" if arg2 is None else arg1
        valor = arg1 if arg2 is None else arg2
        if _wifi_activo:
            _wifi().enviar_canal(canal, valor)

    def leer(self, canal="default", por_defecto=None):
        if _wifi_activo:
            return _wifi().leer_canal(canal, por_defecto)
        return por_defecto

    def leerTexto(self, canal="default", por_defecto=None):
        if _wifi_activo:
            return _wifi().leer_texto(canal, por_defecto)
        return por_defecto

    def buscarCanales(self) -> list:
        """Devuelve una lista con los nombres de todos los canales recibidos."""
        if _wifi_activo:
            return _wifi().buscarCanales()
        return []

    def limpiarBuffer(self):
        """Elimina todos los mensajes y datos recibidos previamente."""
        if _wifi_activo:
            _wifi().limpiar_buffer()

    def __getattr__(self, nombre_funcion):
        def empaquetador(*argumentos):
            if not _wifi_activo:
                return None

            funciones_lectura = ['entradaDigital', 'entradaAnalogica', 'sensorDistancia', 'sensorPeso', 'leerTecladoI2C']
            esperar = nombre_funcion in funciones_lectura

            _wifi().enviar_comando_remoto(nombre_funcion, esperar, *argumentos)

            if esperar:
                return _wifi().esperar_respuesta(timeout_ms=500)

        return empaquetador

wifi = _ControlRemotoWiFi()

# ======================================================================
# --- FUNCIONES LOCALES DEL ROBOT --------------------------------------
# ======================================================================

def iniciar(placa="Placa_Clasica", usar_i2c=True, usar_bt=False):
    global _i2c_activo, _bt_activo
    print("\n--- INICIANDO SISTEMA EDA ---")
    eda_core.configurar_placa(placa)

    if usar_i2c:
        _i2c_activo = _i2c().inicializar_bus(eda_core.PINS['I2C'])
    if usar_bt:
        _bt().inicializar_uart()
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

def RGB(n_salida: int, brillo: int = 100, r: int = 255, g: int = 255, b: int = 255, n_led: int = -1, qleds: int = 7):
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

def sensorPeso(n_entrada: int, peso: float = 1) -> int:
    """Retorna el peso en gramos medido por la celda de carga (HX711) en una entrada (1 a 4)."""
    return eda_core.leer_peso(n_entrada, peso)

def buzzer(n_salida: int, volumen: int = 20, nota: int = 9, octava: int = 4):
    """Reproduce un tono musical en el buzzer asignado a una salida (1 a 4)."""
    eda_core.reproducir_tono(n_salida, volumen, nota, octava)

def mapeo(x: int, cero: int = 33, out_min: int = -100, out_max: int = 100, in_min: int = 0, in_max: int = 100) -> int:
    return int(eda_core.mapeo_joystick(x, cero, out_min, out_max, in_min, in_max))

def detenerTodo():
    """Apaga todos los motores, actuadores y limpia las pantallas."""
    eda_core.apagar_todo()
    if _i2c_activo and _eda_i2c is not None:
        _eda_i2c.limpiar_todo()
    print("Robot completamente detenido de forma segura.")

def microfono(n_entrada: int, crudo: bool = False) -> int:
    """Retorna el nivel de sonido (0 a 100%) del micrófono MAX9814 en una entrada (1 a 4)."""
    return eda_core.leer_microfono(n_entrada, crudo)

# ======================================================================
# --- PANTALLA LCD Y TECLADO (Módulo I2C) ------------------------------
# ======================================================================

def printLCD(columna: int, fila: int, texto, direccion: int = None):
    """Escribe texto en una pantalla LCD en la columna y fila indicadas."""
    if _i2c_activo:
        _i2c().escribir_lcd(columna, fila, str(texto), direccion)

def limpiarLCD(direccion: int = None):
    """Borra el contenido de las pantallas LCD."""
    if _i2c_activo:
        _i2c().limpiar_lcd(direccion)

def luzLCD(estado: bool, direccion: int = None):
    """Enciende o apaga la retroiluminación de la pantalla."""
    if _i2c_activo:
        _i2c().controlar_luz(estado, direccion)

def leerTeclado(id_teclado: int = None) -> str:
    """Retorna la tecla pulsada en el teclado matricial o None si no hay pulsación."""
    if _i2c_activo:
        return _i2c().leer_tecla(id_teclado)
    return None

# ======================================================================
# --- PANTALLA OLED ----------------------------------------------------
# ======================================================================

def printOLED(columna: int, fila: int, texto, escala: int = 1):
    """Escribe texto en el OLED en coordenadas de caracteres (8x8 px) y lo muestra en el momento."""
    if _i2c_activo:
        m = _i2c()
        texto = str(texto)
        x0, y0 = columna * 8 * escala, fila * 8 * escala
        ancho, alto = len(texto) * 8 * escala, 8 * escala
        m.oled_borrar_zona(x0, y0, ancho, alto)
        m.oled_print(columna, fila, texto, escala)
        m.oled_mostrar_zona(x0, y0, x0 + ancho - 1, y0 + alto - 1)

def mostrarOLED():
    """Vuelca todo a la pantalla OLED."""
    if _i2c_activo: _i2c().oled_mostrar()

def limpiarOLED():
    """Borra toda la pantalla OLED."""
    if _i2c_activo: _i2c().oled_limpiar()

def luzOLED(estado: bool):
    """Enciende (True) o apaga (False) el display OLED."""
    if _i2c_activo: _i2c().oled_luz(estado)

def invertirOLED(estado: bool):
    """Invierte los colores del OLED."""
    if _i2c_activo: _i2c().oled_invertir(estado)

def contrasteOLED(valor: int):
    """Ajusta el contraste del OLED (0-255)."""
    if _i2c_activo: _i2c().oled_contraste(valor)

def pixelOLED(x: int, y: int, color: int = 1):
    """Dibuja un píxel individual."""
    if _i2c_activo:
        m = _i2c()
        m.oled_pixel(x, y, color)
        m.oled_mostrar_zona(x, y, x, y)

def lineaOLED(x0: int, y0: int, x1: int, y1: int):
    """Dibuja una línea en píxeles."""
    if _i2c_activo:
        m = _i2c()
        m.oled_linea(x0, y0, x1, y1)
        m.oled_mostrar_zona(x0, y0, x1, y1)

def circuloOLED(cx: int, cy: int, radio: int):
    """Dibuja un círculo vacío."""
    if _i2c_activo:
        m = _i2c()
        m.oled_circulo(cx, cy, radio)
        m.oled_mostrar_zona(cx - radio, cy - radio, cx + radio, cy + radio)

def rectOLED(x: int, y: int, ancho: int, alto: int, relleno: bool = False):
    """Dibuja un rectángulo (vacío o relleno)."""
    if _i2c_activo:
        m = _i2c()
        m.oled_rect(x, y, ancho, alto, relleno)
        m.oled_mostrar_zona(x, y, x + ancho - 1, y + alto - 1)

def dibujarOLED(tipo_grafico, titulo: str, v1=None, v2=None, v3=None, v4=None):
    """Genera gráficos automáticos (sismógrafo, vúmetro, tanque, ecualizador, etc)."""
    if _i2c_activo: _i2c().orquestar_grafico(tipo_grafico, titulo, v1, v2, v3, v4)

# ======================================================================
# --- COMUNICACIÓN BLUETOOTH (Módulo BT) -------------------------------
# ======================================================================

def btEnviar(mensaje: str):
    """Envía un mensaje de texto a través del módulo Bluetooth."""
    if _bt_activo:
        _bt().enviar_datos(mensaje)

def btLeer() -> str:
    """Lee los datos recibidos por Bluetooth. Retorna None si no hay datos."""
    if _bt_activo:
        return _bt().leer_datos()
    return None

def btConfigurar(es_maestro: bool, pin_clave: int) -> bool:
    """Configura el rol y la clave del módulo HC-05."""
    return _bt().configurar_modulo(es_maestro, pin_clave)

def escucharBluetooth():
    if not _bt_activo:
        return
    m = _bt()
    paquete = m.leer_puerto_remoto()
    if paquete:
        _ejecutar_paquete(paquete, m)

# ======================================================================
# --- WIFI E INTERNET (Módulo WiFi) ------------------------------------
# ======================================================================

def iniciarAP(ssid="EDA_Red", password="eda12345", canal=6):
    global _wifi_activo
    _wifi_activo = _wifi().iniciar_ap(ssid, password, canal)
    return _wifi_activo

def iniciarSTA(ssid="EDA_Red", password="eda12345"):
    global _wifi_activo
    _wifi_activo = _wifi().iniciar_sta(ssid, password)
    return _wifi_activo

def conectarWifi(ssid="IoT Tecno", password="T3cnoIoT$25"):
    global _wifi_activo
    _wifi_activo = _wifi().iniciar_sta(ssid, password)
    return _wifi_activo

def desconectarWifi():
    """Desconecta el WiFi y apaga la antena para ahorrar energía y RAM."""
    global _wifi_activo
    if _eda_wifi is not None:
        _eda_wifi.desconectarWifi()
    _wifi_activo = False

def escanearRedes() -> list:
    """Devuelve una lista de redes WiFi cercanas (nombre, intensidad dBm)."""
    return _wifi().escanearRedes()

def estadoWifi() -> bool:
    """Devuelve True si está conectado a una red o si el AP está activo."""
    if _eda_wifi is None:
        return False
    return _eda_wifi.estadoWifi()

def nombreRed():
    """Devuelve el nombre (SSID) de la red conectada o None."""
    if _eda_wifi is None:
        return None
    return _eda_wifi.nombreRed()

def intensidadWifi():
    """Devuelve la intensidad de la señal WiFi en dBm o None."""
    if _eda_wifi is None:
        return None
    return _eda_wifi.intensidadWifi()

def ipWifi():
    """Devuelve la dirección IP asignada a la placa o None."""
    if _eda_wifi is None:
        return None
    return _eda_wifi.ipWifi()

def horaActual(gmt: int = -3, formato: str = "texto"):
    """Devuelve la hora actual (GMT-3 por defecto).
    formato: 'texto' ('14:05:09'), 'tupla' (14, 5, 9), 'hora', 'minuto' o 'segundo'."""
    return _wifi().horaActual(gmt, formato)

def fechaActual(gmt: int = -3, formato: str = "texto"):
    """Devuelve la fecha actual (GMT-3 por defecto).
    formato: 'texto' ('24/11/2026'), 'tupla' (2026, 11, 24), 'dia', 'mes' o 'año'."""
    return _wifi().fechaActual(gmt, formato)

def descargarWeb(url: str, max_bytes: int = 2048, timeout: int = 5):
    """Descarga el contenido de texto de una página web de forma segura para la RAM."""
    return _wifi().descargarWeb(url, max_bytes, timeout)

def descargarJSON(url: str, max_bytes: int = 4096, timeout: int = 5):
    """Descarga datos de una API en formato JSON y devuelve un diccionario o lista."""
    return _wifi().descargarJSON(url, max_bytes, timeout)

def enviarDatoWeb(url: str, datos, timeout: int = 5) -> bool:
    """Envía datos (diccionario, lista o texto) por HTTP POST a una URL o webhook."""
    return _wifi().enviarDatoWeb(url, datos, timeout)

def buscarCanales() -> list:
    """Devuelve una lista con los nombres de todos los canales recibidos en la red."""
    if _wifi_activo:
        return _wifi().buscarCanales()
    return []

def escucharWifi():
    if _wifi_activo:
        m = _wifi()
        paquete_wf = m.leer_puerto_remoto()
        if paquete_wf:
            _ejecutar_paquete(paquete_wf, m)

def _ejecutar_paquete(paquete, modulo_red):
    """Función interna que procesa el JSON recibido y activa los motores/sensores."""
    if not isinstance(paquete, dict) or "f" not in paquete:
        return
    nombre_comando = paquete["f"]
    argumentos = paquete.get("a", [])
    requiere_respuesta = paquete.get("req", False)

    if nombre_comando in globals() and callable(globals()[nombre_comando]):
        funcion_local = globals()[nombre_comando]
        try:
            resultado = funcion_local(*argumentos)
            if requiere_respuesta:
                modulo_red.enviar_respuesta(resultado)
        except Exception as e:
            print(f"Error remoto '{nombre_comando}': {e}")

# ======================================================================
# --- INTELIGENCIA ARTIFICIAL (Módulo IA) ------------------------------
# ======================================================================

def leerPrediccion(umbral: int = 85, espera: int = 1000, apagar: bool = True):
    """Retorna la clase detectada por la notebook (Teachable Machine), o None."""
    return _ia().leer_prediccion(umbral, espera, apagar)

# ======================================================================
# --- AYUDA PARA LOS ALUMNOS: printHelp() ------------------------------
# ======================================================================

def printHelp(nombre=None):
    """Muestra todas las funciones de ORT, o el detalle de una: printHelp("sensorPeso")."""
    import sys, gc
    try:
        import eda_help
        eda_help.mostrar(nombre)
        if "eda_help" in sys.modules:
            del sys.modules["eda_help"]
        del eda_help
    except ImportError:
        print("Error: No se encontró eda_help.py en la placa.")
    finally:
        gc.collect()

modelo = "Placa_Clasica"   # Modelo de placa en uso ("N_ESP32" es la misma placa)

time.sleep(0.2)
iniciar(placa=modelo)
