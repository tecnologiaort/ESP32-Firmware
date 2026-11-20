# -*- coding: utf-8 -*-
"""
Módulo Principal EDA (Fachada Unificada)
Uso recomendado para alumnos: from ORT import *
"""
#2026 22-10 Hola

import time
import eda_core
import eda_i2c
import eda_wifi
import eda_bt
import eda_ia

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
                
            funciones_de_lectura = ['entradaDigital', 'entradaAnalogica', 'sensorDistancia', 'sensorPeso', 'leerTeclado']
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
                
            funciones_lectura = ['entradaDigital', 'entradaAnalogica', 'sensorDistancia', 'sensorPeso', 'leerTecladoI2C']
            esperar = nombre_funcion in funciones_lectura
            
            eda_wifi.enviar_comando_remoto(nombre_funcion, esperar, *argumentos)
            
            if esperar:
                return eda_wifi.esperar_respuesta(timeout_ms=500)
                
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
    """Retorna el peso en gramos medido por la celda de carga (HX711) en una entrada (1 a 4).
    peso: capacidad de la celda en kg (1 por defecto; poner 5 para una de 5 kg, 20 para una de 20 kg, etc.).
    La primera lectura hace la tara: la balanza tiene que estar vacía.
    Retorna -1 si no hay ninguna celda conectada en esa entrada."""
    return eda_core.leer_peso(n_entrada, peso)

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

def microfono(n_entrada: int, crudo: bool = False) -> int:
    """Retorna el nivel de sonido (0 a 100%) del micrófono MAX9814 en una entrada (1 a 4).
    Con crudo=True devuelve el valor sin escalar (solo para calibrar)."""
    return eda_core.leer_microfono(n_entrada, crudo)
    
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
    """Escribe texto en el OLED en coordenadas de caracteres (8x8 px) y lo muestra en el momento.
    Borra lo que había en ese lugar, así un valor nuevo reemplaza al anterior (igual que printLCD)."""
    if _i2c_activo:
        texto = str(texto)
        x0, y0 = columna * 8 * escala, fila * 8 * escala
        ancho, alto = len(texto) * 8 * escala, 8 * escala
        eda_i2c.oled_borrar_zona(x0, y0, ancho, alto)
        eda_i2c.oled_print(columna, fila, texto, escala)
        eda_i2c.oled_mostrar_zona(x0, y0, x0 + ancho - 1, y0 + alto - 1)

def mostrarOLED():
    """Vuelca todo a la pantalla OLED. Ya no hace falta: cada función de dibujo muestra lo suyo sola."""
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
    if _i2c_activo:
        eda_i2c.oled_pixel(x, y, color)
        eda_i2c.oled_mostrar_zona(x, y, x, y)

def lineaOLED(x0: int, y0: int, x1: int, y1: int):
    """Dibuja una línea en píxeles."""
    if _i2c_activo:
        eda_i2c.oled_linea(x0, y0, x1, y1)
        eda_i2c.oled_mostrar_zona(x0, y0, x1, y1)

def circuloOLED(cx: int, cy: int, radio: int):
    """Dibuja un círculo vacío."""
    if _i2c_activo:
        eda_i2c.oled_circulo(cx, cy, radio)
        eda_i2c.oled_mostrar_zona(cx - radio, cy - radio, cx + radio, cy + radio)

def rectOLED(x: int, y: int, ancho: int, alto: int, relleno: bool = False):
    """Dibuja un rectángulo (vacío o relleno)."""
    if _i2c_activo:
        eda_i2c.oled_rect(x, y, ancho, alto, relleno)
        eda_i2c.oled_mostrar_zona(x, y, x + ancho - 1, y + alto - 1)

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

def conectarWifi(ssid="IoT Tecno", password="T3cnoIoT$25"):
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

# ======================================================================
# --- INTELIGENCIA ARTIFICIAL (Módulo IA) ------------------------------
# ======================================================================

def leerPrediccion(umbral: int = 85, espera: int = 1000, apagar: bool = True):
    """Retorna la clase detectada por la notebook (Teachable Machine), o None si no hay
    dato nuevo o la confianza es menor al umbral (0 a 100%).
    Si pasan 'espera' ms sin una predicción confiable, apaga las salidas digitales 1 a 4
    (poner apagar=False para que no las apague)."""
    return eda_ia.leer_prediccion(umbral, espera, apagar)

# ======================================================================
# --- AYUDA PARA LOS ALUMNOS: printHelp() ------------------------------
# ======================================================================
# (nombre, cómo se usa, qué hace, ejemplo)
_AYUDA = (
    ("ENTRADAS Y SENSORES", (
        ("entradaDigital", "entradaDigital(entrada)", "Lee un pulsador o sensor digital: devuelve 0 o 1. Entradas 1 a 4.", "if entradaDigital(1) == 1:"),
        ("entradaAnalogica", "entradaAnalogica(entrada)", "Lee un potenciómetro o sensor analógico: devuelve 0 a 100 (%). Entradas 1 a 4.", "valor = entradaAnalogica(2)"),
        ("sensorDistancia", "sensorDistancia(entrada)", "Distancia en cm del sensor ultrasónico. Devuelve -1 si no mide.", "cm = sensorDistancia(1)"),
        ("sensorPeso", "sensorPeso(entrada, kg=1)", "Peso en gramos de la celda de carga. El 2do dato es la capacidad de la celda en kg (1 o 5). Tiene que estar vacía al arrancar. Devuelve -1 si no hay celda.", "gramos = sensorPeso(2, 5)"),
        ("microfono", "microfono(entrada)", "Nivel de sonido del micrófono, de 0 a 100 (%).", "ruido = microfono(3)"),
        ("leerTeclado", "leerTeclado()", "Tecla apretada en el teclado matricial, o None si no hay ninguna.", "tecla = leerTeclado()"),
    )),
    ("SALIDAS Y MOTORES", (
        ("salidaDigital", "salidaDigital(salida, estado)", "Prende (True) o apaga (False) un LED o relé. Salidas 1 a 4.", "salidaDigital(1, True)"),
        ("salidaAnalogica", "salidaAnalogica(salida, potencia)", "Potencia de 0 a 100 (%) en una salida (LED que se atenúa, motor). Salidas 1 a 4.", "salidaAnalogica(2, 50)"),
        ("servomotor", "servomotor(salida, angulo)", "Mueve un servo a un ángulo de 0 a 180 grados.", "servomotor(1, 90)"),
        ("motorRC", "motorRC(salida, velocidad)", "Motor de giro continuo: velocidad de -100 (atrás) a 100 (adelante). 0 = quieto.", "motorRC(2, 60)"),
        ("buzzer", "buzzer(salida, volumen, nota, octava)", "Toca una nota. nota: 0=Do 2=Re 4=Mi 5=Fa 7=Sol 9=La 11=Si. nota=-1 lo apaga.", "buzzer(3, 20, 0, 4)"),
        ("RGB", "RGB(salida, brillo, r, g, b)", "Prende los LEDs RGB (NeoPixel). brillo 0 a 100, colores 0 a 255.", "RGB(1, 50, 255, 0, 0)"),
        ("detenerTodo", "detenerTodo()", "Apaga motores, salidas y pantallas.", "detenerTodo()"),
    )),
    ("PANTALLA OLED", (
        ("printOLED", "printOLED(columna, fila, texto, tamaño=1)", "Escribe texto o números. Reemplaza lo que había en ese lugar. Tamaño 1: 16 columnas x 8 filas.", 'printOLED(0, 0, "Hola", 2)'),
        ("limpiarOLED", "limpiarOLED()", "Borra toda la pantalla.", "limpiarOLED()"),
        ("dibujarOLED", "dibujarOLED(tipo, titulo, valor)", "Gráfico listo de un valor 0 a 100. Tipos: sismografo, tanque, vumetro, perilla, barra, robot_feliz, robot_enojado, robot_loco, ecualizador.", 'dibujarOLED("tanque", "Agua", 70)'),
        ("pixelOLED", "pixelOLED(x, y)", "Prende un punto. La pantalla mide 128 x 64 píxeles.", "pixelOLED(64, 32)"),
        ("lineaOLED", "lineaOLED(x0, y0, x1, y1)", "Dibuja una línea entre dos puntos.", "lineaOLED(0, 0, 127, 63)"),
        ("rectOLED", "rectOLED(x, y, ancho, alto, relleno=False)", "Dibuja un rectángulo (relleno=True lo pinta).", "rectOLED(10, 10, 50, 20)"),
        ("circuloOLED", "circuloOLED(x, y, radio)", "Dibuja un círculo.", "circuloOLED(64, 32, 20)"),
        ("luzOLED", "luzOLED(estado)", "Prende (True) o apaga (False) la pantalla.", "luzOLED(False)"),
        ("invertirOLED", "invertirOLED(estado)", "Invierte los colores (True / False).", "invertirOLED(True)"),
        ("contrasteOLED", "contrasteOLED(valor)", "Contraste de 0 a 255.", "contrasteOLED(100)"),
    )),
    ("PANTALLA LCD", (
        ("printLCD", "printLCD(columna, fila, texto)", "Escribe en el LCD. Columnas 1 a 16, filas 1 y 2.", 'printLCD(1, 1, "Hola")'),
        ("limpiarLCD", "limpiarLCD()", "Borra el LCD.", "limpiarLCD()"),
        ("luzLCD", "luzLCD(estado)", "Prende (True) o apaga (False) la luz del LCD.", "luzLCD(True)"),
    )),
    ("INTELIGENCIA ARTIFICIAL", (
        ("leerPrediccion", "leerPrediccion(umbral=85)", "Clase que detectó Teachable Machine en la notebook (0, 1, 2...), o None si no está segura. umbral: confianza mínima en %.", "clase = leerPrediccion()"),
    )),
    ("BLUETOOTH Y WIFI", (
        ("btEnviar", "btEnviar(mensaje)", "Manda un texto por Bluetooth.", 'btEnviar("Hola")'),
        ("btLeer", "btLeer()", "Lee lo que llegó por Bluetooth, o None.", "dato = btLeer()"),
        ("btConfigurar", "btConfigurar(es_maestro, clave)", "Configura el módulo HC-05 (en modo AT). Clave de 4 dígitos.", "btConfigurar(False, 1234)"),
        ("iniciarAP", "iniciarAP(nombre, clave)", "Crea una red WiFi propia para conectar otra placa.", 'iniciarAP("Robot1", "clave1234")'),
        ("iniciarSTA", "iniciarSTA(nombre, clave)", "Se conecta a la red de otra placa.", 'iniciarSTA("Robot1", "clave1234")'),
        ("wifi.enviar", "wifi.enviar(canal, valor)", "Manda un valor a la otra placa por un canal con nombre.", 'wifi.enviar("vel", 50)'),
        ("wifi.leer", "wifi.leer(canal)", "Último valor recibido en ese canal (None si no llegó nada).", 'v = wifi.leer("vel")'),
        ("escucharWifi", "escucharWifi()", "Ejecuta las órdenes que manda la otra placa. Va dentro del while.", "escucharWifi()"),
    )),
    ("UTILIDADES", (
        ("mapeo", "mapeo(x)", "Convierte el 0 a 100 de un joystick en -100 a 100 (centro en 0).", "giro = mapeo(entradaAnalogica(1))"),
        ("printHelp", "printHelp(\"funcion\")", "Muestra esta lista, o el detalle de una función.", 'printHelp("sensorPeso")'),
    )),
)

def printHelp(nombre=None):
    """Muestra todas las funciones de ORT, o el detalle de una: printHelp("sensorPeso")."""
    if nombre is None:
        print("\n===== FUNCIONES DISPONIBLES =====")
        for categoria, funciones in _AYUDA:
            print("\n--", categoria, "--")
            for _, uso, que_hace, _ in funciones:
                print("  " + uso)
        print('\nPara ver el detalle y un ejemplo: printHelp("nombreDeLaFuncion")\n')
        return
    nombre = str(nombre)
    buscado = nombre.replace("(", "").replace(")", "").strip().lower()
    for categoria, funciones in _AYUDA:
        for clave, uso, que_hace, ejemplo in funciones:
            if clave.lower() == buscado:
                print("\n" + uso)
                print("  " + que_hace)
                print("  Ejemplo:  " + ejemplo + "\n")
                return
    print('No existe "' + nombre + '". Escribí printHelp() para ver todas las funciones.')

modelo = "Placa_Clasica"   # Modelo de placa en uso ("N_ESP32" es la misma placa)

time.sleep(0.2)
iniciar(placa=modelo)