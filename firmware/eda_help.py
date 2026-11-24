# -*- coding: utf-8 -*-
"""
Módulo de Ayuda EDA (eda_help.py)
Se importa bajo demanda desde ORT.printHelp() y se libera de la RAM al terminar.
"""

_AYUDA = (
    ("ENTRADAS Y SENSORES", (
        ("entradaDigital", "entradaDigital(entrada)", "Lee un pulsador o sensor digital: devuelve 0 o 1. Entradas 1 a 4.", "if entradaDigital(1) == 1:"),
        ("entradaAnalogica", "entradaAnalogica(entrada)", "Lee un potenciómetro o sensor analógico: devuelve 0 a 100 (%). Entradas 1 a 4.", "valor = entradaAnalogica(2)"),
        ("sensorDistancia", "sensorDistancia(entrada)", "Distancia en cm del sensor ultrasónico. Devuelve -1 si no mide.", "cm = sensorDistancia(1)"),
        ("sensorPeso", "sensorPeso(entrada, kg=1)", "Peso en gramos de la celda de carga. El 2do dato es la capacidad de la celda en kg (1 o 5). Tiene que estar vacía al arrancar. Devuelve -1 si no hay celda.", "gramos = sensorPeso(2, 5)"),
        ("microfono", "microfono(entrada, crudo=False)", "Nivel de sonido del micrófono, de 0 a 100 (%).", "ruido = microfono(3)"),
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
        ("mostrarOLED", "mostrarOLED()", "Vuelca todo el buffer a la pantalla OLED (opcional, las funciones ya dibujan solas).", "mostrarOLED()"),
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
    ("BLUETOOTH", (
        ("btEnviar", "btEnviar(mensaje)", "Manda un texto por Bluetooth.", 'btEnviar("Hola")'),
        ("btLeer", "btLeer()", "Lee lo que llegó por Bluetooth, o None.", "dato = btLeer()"),
        ("btConfigurar", "btConfigurar(es_maestro, clave)", "Configura el módulo HC-05 (en modo AT). Clave de 4 dígitos.", "btConfigurar(False, 1234)"),
        ("bt.enviar", "bt.enviar(canal, valor)", "Manda un valor por Bluetooth en un canal con nombre.", 'bt.enviar("vel", 50)'),
        ("bt.leer", "bt.leer(canal)", "Último número recibido por Bluetooth en ese canal.", 'v = bt.leer("vel")'),
        ("bt.leerTexto", "bt.leerTexto(canal)", "Último texto recibido por Bluetooth en ese canal.", 'msg = bt.leerTexto("chat")'),
        ("escucharBluetooth", "escucharBluetooth()", "Ejecuta las órdenes que manda otra placa por Bluetooth. Va dentro del while.", "escucharBluetooth()"),
    )),
    ("WIFI Y CANALES", (
        ("conectarWifi", "conectarWifi(nombre, clave)", "Conecta la placa a una red WiFi con internet (por defecto la del taller).", 'conectarWifi("MiWiFi", "12345678")'),
        ("desconectarWifi", "desconectarWifi()", "Desconecta el WiFi y apaga la antena para ahorrar RAM y energía.", "desconectarWifi()"),
        ("iniciarAP", "iniciarAP(nombre, clave)", "Crea una red WiFi propia para conectar otra placa.", 'iniciarAP("Robot1", "clave1234")'),
        ("iniciarSTA", "iniciarSTA(nombre, clave)", "Se conecta a la red de otra placa.", 'iniciarSTA("Robot1", "clave1234")'),
        ("estadoWifi", "estadoWifi()", "Devuelve True si está conectado al WiFi, o False si no.", "if estadoWifi():"),
        ("nombreRed", "nombreRed()", "Devuelve el nombre (SSID) de la red conectada, o None.", "red = nombreRed()"),
        ("intensidadWifi", "intensidadWifi()", "Devuelve la fuerza de la señal WiFi en dBm (ej: -60 es buena, -85 débil).", "senal = intensidadWifi()"),
        ("ipWifi", "ipWifi()", "Devuelve la dirección IP asignada a la placa, o None.", "mi_ip = ipWifi()"),
        ("escanearRedes", "escanearRedes()", "Busca redes WiFi cercanas y devuelve una lista de (nombre, señal).", "redes = escanearRedes()"),
        ("wifi.enviar", "wifi.enviar(canal, valor)", "Manda un valor a la otra placa por un canal con nombre.", 'wifi.enviar("vel", 50)'),
        ("wifi.leer", "wifi.leer(canal)", "Último número recibido en ese canal (None si no llegó nada).", 'v = wifi.leer("vel")'),
        ("wifi.leerTexto", "wifi.leerTexto(canal)", "Último texto recibido en ese canal (None si no llegó nada).", 'msg = wifi.leerTexto("chat")'),
        ("wifi.limpiarBuffer", "wifi.limpiarBuffer()", "Borra todos los mensajes y datos viejos recibidos por WiFi.", "wifi.limpiarBuffer()"),
        ("buscarCanales", "buscarCanales()", "Devuelve una lista con todos los canales que enviaron datos en la red.", "canales = buscarCanales()"),
        ("escucharWifi", "escucharWifi()", "Ejecuta las órdenes que manda la otra placa. Va dentro del while.", "escucharWifi()"),
    )),
    ("INTERNET Y RELOJ", (
        ("horaActual", "horaActual(gmt=-3, formato=\"texto\")", "Hora actual por internet. formato: \"texto\", \"tupla\", \"hora\", \"minuto\" o \"segundo\".", 'h, m, s = horaActual(formato="tupla")'),
        ("fechaActual", "fechaActual(gmt=-3, formato=\"texto\")", "Fecha actual por internet. formato: \"texto\", \"tupla\", \"dia\", \"mes\" o \"año\".", 'hoy = fechaActual()'),
        ("descargarWeb", "descargarWeb(url, max_bytes=2048)", "Descarga el texto de una página web cuidando la RAM del ESP32.", 'txt = descargarWeb("http://example.com")'),
        ("descargarJSON", "descargarJSON(url, max_bytes=4096)", "Descarga datos de una API en JSON y devuelve un diccionario o lista.", 'clima = descargarJSON("http://api...")'),
        ("enviarDatoWeb", "enviarDatoWeb(url, datos)", "Envía un diccionario o texto por HTTP POST a una web o webhook.", 'enviarDatoWeb("http://...", {"temp": 24})'),
    )),
    ("UTILIDADES", (
        ("iniciar", "iniciar(placa, usar_i2c=True, usar_bt=False)", "Inicializa la placa y los módulos seleccionados (se ejecuta sola al importar ORT).", 'iniciar("Placa_Clasica", True, True)'),
        ("mapeo", "mapeo(x)", "Convierte el 0 a 100 de un joystick en -100 a 100 (centro en 0).", "giro = mapeo(entradaAnalogica(1))"),
        ("printHelp", "printHelp(\"funcion\")", "Muestra esta lista, o el detalle de una función.", 'printHelp("sensorPeso")'),
    )),
)

def mostrar(nombre=None):
    """Muestra todas las funciones de ORT, o el detalle de una función puntual."""
    if nombre is None:
        print("\n===== FUNCIONES DISPONIBLES =====")
        for categoria, funciones in _AYUDA:
            print("\n--", categoria, "--")
            for _, uso, _, _ in funciones:
                print("  " + uso)
        print('\nPara ver el detalle y un ejemplo: printHelp("nombreDeLaFuncion")\n')
        return

    nombre = str(nombre)
    buscado = nombre.replace("(", "").replace(")", "").strip().lower()
    for _, funciones in _AYUDA:
        for clave, uso, que_hace, ejemplo in funciones:
            if clave.lower() == buscado:
                print("\n" + uso)
                print("  " + que_hace)
                print("  Ejemplo:  " + ejemplo + "\n")
                return

    print('No existe "' + nombre + '". Escribí printHelp() para ver todas las funciones.')
