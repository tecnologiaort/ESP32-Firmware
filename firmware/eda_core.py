# -*- coding: utf-8 -*-
"""
Módulo Interno CORE (eda_core.py)
Gestiona directamente el hardware del ESP32 (Pines, ADC, PWM, NeoPixel, Micrófono, Celda de carga).

"""

import machine
import utime
import math
import neopixel
from machine import Pin, PWM, ADC

# ======================================================================
# --- 1. DICCIONARIOS Y CONFIGURACIÓN DE PINES -------------------------
# ======================================================================

PIN_MAPS = {
    'Placa_Clasica': {
        'digital_outputs': [0, 27, 25, 32],
        'adc_inputs': [36, 34, 12, 2],
        'digital_inputs': [39, 35, 4, 15],
        'servo_pins': [13, 14, 26, 33],
        'I2C': (22, 21),
        'us_outputs': [19, 18, 4, 15],
        'digital_data': [10, 5, 23],
        
    },
    'super_mini': {
        'digital_outputs': [38, 35, 36, 16],
        'adc_inputs': [1, 3, 2, 5],
        'digital_inputs': [4, 7, 6, 34],
        'servo_pins': [37, 18, 17, 21],
        'I2C': (9, 8),
        'us_outputs': [4, 7, 6, 34],
        'digital_data': []
    },
    'WEMOS': {
        'digital_outputs': [26, 17, 27, 12],
        'adc_inputs': [2, 4, 35, 34],
        'digital_inputs': [5, 23, 19, 18],
        'servo_pins': [25, 16, 14, 13],
        'I2C': (22, 21),
        'us_outputs': [5, 23, 19, 18]
    },
    'ESP32': {
        'digital_outputs': [32, 25, 27, 12],
        'adc_inputs': [35, 34, 39, 36],
        'digital_inputs': [4, 2, 15, 0],
        'servo_pins': [33, 26, 14, 13],
        'I2C': (22, 21),
        'us_outputs': [4, 2, 15, 0]
    }
}

# 'N_ESP32' es otro nombre de la misma placa que 'Placa_Clasica' (mismos pines)
PIN_MAPS['N_ESP32'] = PIN_MAPS['Placa_Clasica']

# Variables de estado global
_placa_actual = None
PINS = None
_matrices_neopixel = {}

# Listas de objetos de hardware
_digital_outputs = []
_digital_data = []
_digital_inputs = []
_us_outputs = []
_adc_inputs = []
_servo_pwms = [None, None, None, None]

salidasDigitales = [False,False,False,False,False,False,False,False]

try:
    for pin_num in PINS['servo_pins']:
        try:
            pwm_zombie = PWM(Pin(pin_num))
            pwm_zombie.deinit()
        except:
            pass
except:
    pass
# Tablas de calibración para ADC no lineal (Específico para WEMOS Pin 2)
CAL_LEIDO_PIN2_RAW = [0, 120, 215, 300, 410, 570, 680, 832, 950, 1215, 1600, 2060, 4095]
CAL_REAL_PIN2_RAW  = [0, 429, 900, 1315, 1825, 2300, 2550, 2815, 3000, 3300, 3600, 3940, 4095]

# Calibración del micrófono MAX9814
_MIC_RUIDO = 25        # Piso de ruido medido en silencio (se toma como 0)
_MIC_MAX = 600         # Valor crudo que se considera 100% (ajustar con la calibración)
_MIC_MUESTRAS = 400    # Cantidad de muestras por lectura (~10-15 ms)
_MIC_SUBIDA = 0.6      # Qué tan rápido sube (0-1)
_MIC_BAJADA = 0.15     # Qué tan rápido baja (0-1)
_mic_nivel = [0.0, 0.0, 0.0, 0.0]

# Celda de carga HX711 (función sensorPeso)
# Cuentas del HX711 que da una celda de 1 mV/V (la mayoría) cuando tiene encima su peso máximo.
# Cuentas por gramo = _PESO_CUENTAS_MAX / (capacidad en gramos). Ej: 1 kg -> 2147, 5 kg -> 429.
_PESO_CUENTAS_MAX = 2147484.0
# Celdas medidas con un peso conocido: {capacidad en kg: cuentas por gramo}.
# Tienen prioridad sobre la cuenta teórica de arriba. Para calibrar otra: factor = cuentas / gramos reales.
_PESO_CALIBRADAS = {
    1: 420.0,    # celda de 1 kg (valor de la librería original)
    5: 429.5,    # celda de 5 kg (verificada: mide bien)
}
_PESO_REINTENTO_MS = 1000     # Si no hay celda, cada cuánto se la vuelve a buscar
_celdas = {}                  # {n_entrada: objeto _HX711}
_peso_ultimo_intento = [None, None, None, None]

# ======================================================================
# --- 2. FUNCIONES DE INICIALIZACIÓN -----------------------------------
# ======================================================================

def configurar_placa(nombre_placa: str):
    """Inicializa los objetos Pin, ADC y PWM según la placa elegida."""
    global _placa_actual, PINS, _digital_outputs, _digital_inputs, _us_outputs, _adc_inputs
    
    if nombre_placa not in PIN_MAPS:
        print(f"Error: Placa '{nombre_placa}' no válida. Usando Placa_Clasica por defecto.")
        nombre_placa = "Placa_Clasica"
        
    _placa_actual = nombre_placa
    PINS = PIN_MAPS[_placa_actual]
    
    # Inicializar salidas y apagar por seguridad
    _digital_outputs = [Pin(p, Pin.OUT) for p in PINS['digital_outputs']]
    for pin in _digital_outputs:
        pin.value(0)
    _digital_data = [Pin(p, Pin.OUT) for p in PINS.get('digital_data', [])]
    for pin in _digital_data:
        pin.value(0)
        
    # En el ESP32 clásico los GPIO 34-39 son solo entrada y no tienen pull-down interno
    # (en la super_mini, que es otro chip, esos pines son normales)
    sin_pull = () if _placa_actual == 'super_mini' else (34, 35, 36, 37, 38, 39)
    _digital_inputs = [Pin(p, Pin.IN) if p in sin_pull else Pin(p, Pin.IN, Pin.PULL_DOWN) for p in PINS['digital_inputs']]
    _us_outputs = [Pin(p, Pin.IN) if p in sin_pull else Pin(p, Pin.IN, Pin.PULL_DOWN) for p in PINS['us_outputs']]
    
    # Inicializar ADCs
    _adc_inputs = []
    for p in PINS['adc_inputs']:
        adc = ADC(Pin(p))
        adc.atten(ADC.ATTN_11DB) # Rango de 0 a 3.3V
        _adc_inputs.append(adc)
    
    escribir_salida_analogica(1,0,1)
    escribir_salida_analogica(2,0,1)
    escribir_salida_analogica(3,0,1)
    escribir_salida_analogica(4,0,1)
    
    
    print(f"Hardware base iniciado para: {_placa_actual}")

def apagar_todo():
    """Libera recursos y apaga motores de forma segura."""
    for i in range(4):
        if _servo_pwms[i] is not None:
            _servo_pwms[i].deinit()
            _servo_pwms[i] = None
        if i < len(_digital_outputs):
            _digital_outputs[i].value(0)


# ======================================================================
# --- 3. FUNCIONES DE UTILIDAD MATEMÁTICA ------------------------------
# ======================================================================

def _map_value(x, in_min, in_max, out_min, out_max):
    if (in_max - in_min) == 0: return out_min
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

def _interpolar(x, x_puntos, y_puntos):
    if x <= x_puntos[0]: return y_puntos[0]
    if x >= x_puntos[-1]: return y_puntos[-1]
    try:
        for i in range(len(x_puntos) - 1):
            if x >= x_puntos[i] and x <= x_puntos[i+1]:
                return _map_value(x, x_puntos[i], x_puntos[i+1], y_puntos[i], y_puntos[i+1])
    except:
        pass
    return y_puntos[0]

def mapeo_joystick(x, cero, out_min, out_max, in_min, in_max) -> int:
    if cero - 3 < x < cero + 3:
        x = cero
    
    if x > cero:
        return _map_value(x, cero, in_max, (out_max + out_min)/2, out_max)
    else:
        return _map_value(x, in_min, cero, out_min, (out_max + out_min)/2)

    


# ======================================================================
# --- 4. EJECUCIÓN DE HARDWARE (Sensores y Actuadores) -----------------
# ======================================================================

def controlar_neopixel(n_salida: int, brillo: int, r: int, g: int, b: int, n_led: int, qleds: int):
    if not (1 <= n_salida <= len(PINS.get('digital_data', []))):
        print(f"Error: salida digital_data {n_salida} fuera de rango.")
        return
    estadoP = salidasDigitales[n_salida]
    escribir_salida_digital(n_salida, False)
    # Accedemos al pin mapeado según la placa configurada
    pin_num = PINS['digital_data'][n_salida - 1]
    pin = Pin(pin_num, Pin.OUT)

    if n_salida not in _matrices_neopixel:
        _matrices_neopixel[n_salida] = neopixel.NeoPixel(pin, qleds)

    np = _matrices_neopixel[n_salida]

    brillo = max(0, min(100, brillo))
    factor = brillo / 100.0
    r_adj = int(r * factor)
    g_adj = int(g * factor)
    b_adj = int(b * factor)

    if n_led == -1:
        for i in range(qleds):
            np[i] = (r_adj, g_adj, b_adj)
    else:
        if 0 <= n_led <= qleds-1:
            np[n_led] = (r_adj, g_adj, b_adj)
        else:
            print(f"Error: n_led debe estar entre 0 y {qleds}")
            utime.sleep_us(100000)
            escribir_salida_digital(n_salida, estadoP)
            return

    np.write()
    pin.value(0)
    
    escribir_salida_digital(n_salida, estadoP)
    
def leer_entrada_digital(n_entrada: int) -> int:
    if 1 <= n_entrada <= 4:
        return _digital_inputs[n_entrada - 1].value()
    print(f"Error: entradaDigital {n_entrada} fuera de rango (1-4).")
    return -1

def leer_entrada_analogica(n_entrada: int) -> int:
    if not (1 <= n_entrada <= 4):
        print(f"Error: entradaAnalogica {n_entrada} fuera de rango (1-4).")
        return -1
    try:
        idx = n_entrada - 1
        valor_raw = _adc_inputs[idx].read()
        porcentaje = 0.0
        
        if _placa_actual == 'WEMOS' and n_entrada == 1:
            valor_corregido = _interpolar(valor_raw, CAL_LEIDO_PIN2_RAW, CAL_REAL_PIN2_RAW)
            porcentaje = (valor_corregido / 4050) * 100
        elif _placa_actual in ("Placa_Clasica", "N_ESP32"):
            porcentaje = int(1.315789 * (valor_raw / 4050) * 100)
        elif _placa_actual == "ESP32_S2":
            porcentaje = int(0.495 * (valor_raw / 4050) * 100) - 2
        else:
            porcentaje = (valor_raw / 4050) * 100
            
        return max(0, min(100, int(porcentaje))) # Acotar entre 0 y 100
    except Exception as e:
        print(f"Error en ADC: {e}")
        return -1
    
def leer_entrada_analogica_RAW(n_entrada: int) -> float:
    if not (1 <= n_entrada <= 4):
        print(f"Error: entradaAnalogica {n_entrada} fuera de rango (1-4).")
        return -1
    try:
        idx = n_entrada - 1
        valor_raw = _adc_inputs[idx].read()
        porcentaje = 0.0
        
        if _placa_actual == 'WEMOS' and n_entrada == 1:
            valor_corregido = _interpolar(valor_raw, CAL_LEIDO_PIN2_RAW, CAL_REAL_PIN2_RAW)
            porcentaje = (valor_corregido / 4050) * 100
        elif _placa_actual in ("Placa_Clasica", "N_ESP32"):
            porcentaje = int(1.315789 * (valor_raw / 4050) * 100)
        else:
            porcentaje = (valor_raw / 4050) * 100
            
        return max(0, min(100, int(porcentaje))) # Acotar entre 0 y 100
    except Exception as e:
        print(f"Error en ADC: {e}")
        return -1

def escribir_salida_digital(n_salida: int, estado: bool):
    if 1 <= n_salida <= 4:
        _digital_outputs[n_salida - 1].value(1 if estado else 0)
        salidasDigitales[n_salida] = estado
    else:
        print(f"Error: salidaDigital {n_salida} fuera de rango (1-4).")


def _obtener_duty(potencia):
    return int((potencia / 100) * 65535)

def _obtener_pwm(n_salida: int, freq: int) -> PWM:
    """Función interna para inicializar o reconfigurar un canal PWM."""
    idx = n_salida - 1
    pin_num = PINS['servo_pins'][idx]
    
    if _servo_pwms[idx] is None:
        _servo_pwms[idx] = PWM(Pin(pin_num), freq=freq)
    else:
        _servo_pwms[idx].freq(freq) # Actualizar frecuencia por si se usó para otra cosa
    return _servo_pwms[idx]

def escribir_salida_analogica(n_salida: int, potencia: int, frecuencia = 1000):
    if 1 <= n_salida <= 4:
        # Aseguramos que la potencia esté dentro del rango 0-100
        potencia = max(0, min(100, potencia))
        
        # Convertimos el porcentaje (0-100) a un entero de 16 bits (0-65535)
        duty_16bit = int((potencia / 100) * 65534) + 1
        
        pwm = _obtener_pwm(n_salida, freq=frecuencia)
        pwm.duty_u16(duty_16bit)
    else:
        print(f"Error: salidaAnalogica {n_salida} fuera de rango (1-4).")

def escribir_motor_rc(n_salida: int, velocidad: int):
    if 1 <= n_salida <= 4:
        velocidad = max(-100, min(100, velocidad))
        duty_16bit = _map_value(velocidad, -100, 100, 1986, 7687)
        pwm = _obtener_pwm(n_salida, freq=50)
        pwm.duty_u16(int(duty_16bit))
    else:
        print(f"Error: motorRC {n_salida} fuera de rango (1-4).")

def escribir_servomotor(n_salida: int, angulo: int):
    if 1 <= n_salida <= 4:
        angulo = max(0, min(180, angulo))
        duty_16bit = _map_value(angulo, 0, 180, 1986, 7687)
        pwm = _obtener_pwm(n_salida, freq=50)
        pwm.duty_u16(int(duty_16bit))
    else:
        print(f"Error: servomotor {n_salida} fuera de rango (1-4).")

def leer_distancia(n_entrada: int) -> float:
    if not (1 <= n_entrada <= 4):
        print(f"Error: sensorDistancia número {n_entrada} fuera de rango (1-4).")
        return -1
     
    # NOTA: Asegúrate de que los pines en 'adc_inputs' sean GPIOs digitales normales (ej. 12, 13, 14, etc.)
    trigger_pin_num = PINS['us_outputs'][n_entrada - 1] 
    echo_pin_num = PINS['adc_inputs'][n_entrada - 1]     
    
    trigger = Pin(trigger_pin_num, Pin.OUT)
    echo = Pin(echo_pin_num, Pin.IN)
    
    # Asegurar estado bajo inicial
    trigger.value(0)
    utime.sleep_us(5)
 
    # Lanzar el pulso de disparo
    trigger.value(1)
    utime.sleep_us(10)
    trigger.value(0)
    
    # --- SE ELIMINÓ LA LÍNEA QUE CAMBIABA EL TRIGGER A Pin.IN ---
    
    try:
        # Medimos el pulso en alto (1) en el pin ECHO
        duration = machine.time_pulse_us(echo, 1, 30000)
    except OSError:
        return -1 
        
    if duration < 0:
        return -1 # Timeout o lectura errónea
        
    # Cálculo preciso de la distancia
    dist_cm = (duration * 0.0343) / 2
    return round(dist_cm, 2)

def reproducir_tono(n_salida: int, volumen: int, nota: int, octava: int):
    if not (1 <= n_salida <= 4):
        print("Error: buzzer fuera de rango (1-4).")
        return

    # Frecuencias base de Do0 a Si0
    notas_base = [16.35, 17.32, 18.35, 19.45, 20.60, 21.83, 
                  23.12, 24.50, 25.96, 27.50, 29.14, 30.87]
    
    if nota == -1 or volumen <= 0:
        if _servo_pwms[n_salida - 1] is not None:
            _servo_pwms[n_salida - 1].duty_u16(0)
        return

    frecuencia = int(notas_base[nota] * (2 ** octava))
    frecuencia = max(frecuencia, 10) # MicroPython falla bajo los 10Hz
    
    pwm = _obtener_pwm(n_salida, freq=frecuencia)
    
    # Mapeo logarítmico del volumen para mejor percepción auditiva
    volumen_log = (math.pow(10, volumen / 100) - 1) / 9
    duty = int(volumen_log * 120) * 64
    
    pwm.duty_u16(duty)


def leer_microfono(n_entrada: int, crudo: bool = False) -> int:
    if not (1 <= n_entrada <= 4):
        print(f"Error: microfono {n_entrada} fuera de rango (1-4).")
        return -1

    idx = n_entrada - 1
    adc = _adc_inputs[idx]

    # 1. Tomamos las muestras
    muestras = [adc.read() for _ in range(_MIC_MUESTRAS)]

    # 2. Desvío medio respecto del centro de la señal
    media = sum(muestras) / _MIC_MUESTRAS
    desvio = sum(abs(v - media) for v in muestras) / _MIC_MUESTRAS

    if crudo:
        return int(desvio)  # Solo para calibrar

    # 3. Escalamos a 0-100
    porcentaje = (desvio - _MIC_RUIDO) * 100 / (_MIC_MAX - _MIC_RUIDO)
    porcentaje = max(0, min(100, porcentaje))

    # 4. Suavizado tipo vúmetro: sube rápido, baja lento
    anterior = _mic_nivel[idx]
    coef = _MIC_SUBIDA if porcentaje > anterior else _MIC_BAJADA
    _mic_nivel[idx] = anterior + (porcentaje - anterior) * coef

    return int(_mic_nivel[idx])


# ======================================================================
# --- 5. CELDA DE CARGA HX711 (función sensorPeso) ---------------------
# ======================================================================
# La celda se enchufa en cualquiera de las 4 entradas:
#   DT  -> pin analógico de la entrada (adc_inputs)
#   SCK -> pin de trigger de la entrada (us_outputs)
# La primera lectura hace la tara, así que la balanza tiene que estar vacía en ese momento.

class _HX711:
    def __init__(self, pin_dt, pin_sck):
        self.dt = Pin(pin_dt, Pin.IN, Pin.PULL_DOWN)
        self.sck = Pin(pin_sck, Pin.OUT, value=0)   # SCK en bajo = HX711 encendido
        self.offset = 0

    def _esperar_dato(self, timeout_ms=300):
        # El HX711 baja DT cuando tiene una medición lista
        t0 = utime.ticks_ms()
        while self.dt.value() != 0:
            if utime.ticks_diff(utime.ticks_ms(), t0) > timeout_ms:
                raise OSError("HX711 no responde")
            utime.sleep_us(100)

    def leer_crudo(self):
        self._esperar_dato()
        # Sin interrupciones: si SCK queda en alto más de 60 us el HX711 se apaga
        irq = machine.disable_irq()
        valor = 0
        for _ in range(24):
            self.sck.value(1)
            valor <<= 1
            self.sck.value(0)
            if self.dt.value():
                valor += 1
        self.sck.value(1)        # pulso 25: canal A, ganancia 128
        self.sck.value(0)
        machine.enable_irq(irq)
        # Un HX711 real sube DT apenas termina la lectura y lo deja arriba mientras mide.
        # Si no pasa, la celda se desconectó o lo que hay enchufado no es un HX711.
        if self.dt.value() == 0:
            raise OSError("no es un HX711")
        utime.sleep_us(300)
        if self.dt.value() == 0:
            raise OSError("no es un HX711")
        if valor & 0x800000:     # complemento a 2 (24 bits)
            valor -= 0x1000000
        return valor

    def promedio(self, veces):
        return sum(self.leer_crudo() for _ in range(veces)) / veces

    def tarar(self):
        lecturas = [self.leer_crudo() for _ in range(10)]
        # Un sensor de distancia responde con un único escalón de bits (ej. 000111);
        # una celda real tiene ruido en los bits bajos y nunca da 10 lecturas así
        if all(_es_escalon(v) for v in lecturas):
            raise OSError("no es un HX711")
        self.offset = sum(lecturas) / len(lecturas)

def _es_escalon(valor: int) -> bool:
    """True si los 24 bits son todos 0, todos 1 o un único bloque de unos seguidos."""
    v = valor & 0xFFFFFF
    if v == 0:
        return True
    x = v | (v - 1)
    return (x & (x + 1)) == 0

def _liberar_entrada(idx: int):
    """Devuelve los pines de una entrada a su función normal (analógica + trigger)."""
    Pin(PINS['us_outputs'][idx], Pin.IN, Pin.PULL_DOWN)
    adc = ADC(Pin(PINS['adc_inputs'][idx], Pin.IN, None))
    adc.atten(ADC.ATTN_11DB)
    _adc_inputs[idx] = adc

def _conectar_celda(n_entrada: int):
    """Busca el HX711 en la entrada, hace la tara y lo guarda. Devuelve None si no hay."""
    idx = n_entrada - 1
    _peso_ultimo_intento[idx] = utime.ticks_ms()
    try:
        hx = _HX711(PINS['adc_inputs'][idx], PINS['us_outputs'][idx])
        hx.tarar()
    except OSError:
        _liberar_entrada(idx)
        return None
    _celdas[n_entrada] = hx
    print(f"Celda de carga conectada en entrada {n_entrada} (tara hecha)")
    return hx

def leer_peso(n_entrada: int, peso_kg: float = 1) -> int:
    """Devuelve el peso en gramos de la celda conectada en la entrada (1 a 4).
    peso_kg es la capacidad de la celda en kg (1, 5, 10, 20...).
    Devuelve -1 si no hay ninguna celda conectada en esa entrada."""
    if not (1 <= n_entrada <= 4):
        print(f"Error: sensorPeso {n_entrada} fuera de rango (1-4).")
        return -1
    if not isinstance(peso_kg, (int, float)) or peso_kg <= 0:
        print(f"Error: sensorPeso peso {peso_kg} no válido (la capacidad de la celda en kg, ej. 1 o 5).")
        return -1
    idx = n_entrada - 1

    hx = _celdas.get(n_entrada)
    if hx is None:
        # Sin celda: se la busca como mucho una vez por segundo para no frenar el programa
        ultimo = _peso_ultimo_intento[idx]
        if ultimo is not None and utime.ticks_diff(utime.ticks_ms(), ultimo) < _PESO_REINTENTO_MS:
            return -1
        hx = _conectar_celda(n_entrada)
        if hx is None:
            if ultimo is None:
                print(f"sensorPeso: no hay celda de carga en la entrada {n_entrada}")
            return -1

    try:
        cuentas_por_gramo = _PESO_CALIBRADAS.get(peso_kg) or _PESO_CUENTAS_MAX / (peso_kg * 1000)
        gramos = (hx.promedio(3) - hx.offset) / cuentas_por_gramo
    except OSError:
        # Se desconectó: liberamos la entrada y la seguimos buscando
        _celdas.pop(n_entrada, None)
        _liberar_entrada(idx)
        _peso_ultimo_intento[idx] = utime.ticks_ms()
        print(f"Celda de carga desconectada de la entrada {n_entrada}")
        return -1
    return int(round(gramos))
