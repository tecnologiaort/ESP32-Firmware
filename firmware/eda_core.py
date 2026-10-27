# -*- coding: utf-8 -*-
"""
Módulo Interno CORE (eda_core.py)
Gestiona directamente el hardware del ESP32 (Pines, ADC, PWM).

"""

import machine
import utime
import math
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
        'us_outputs': [19, 18, 4, 15]
    },
    'super_mini': {
        'digital_outputs': [38, 35, 36, 16],
        'adc_inputs': [1, 3, 2, 5],
        'digital_inputs': [4, 7, 6, 34],
        'servo_pins': [37, 18, 17, 21],
        'I2C': (9, 8),
        'us_outputs': [4, 7, 6, 34]
    }
}

# Variables de estado global
_placa_actual = None
PINS = None

# Listas de objetos de hardware
_digital_outputs = []
_digital_inputs = []
_us_outputs = []
_adc_inputs = []
_servo_pwms = [None, None, None, None]

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


# ======================================================================
# --- 2. FUNCIONES DE INICIALIZACIÓN -----------------------------------
# ======================================================================

def configurar_placa(nombre_placa: str):
    """Inicializa los objetos Pin, ADC y PWM según la placa elegida."""
    global _placa_actual, PINS, _digital_outputs, _digital_inputs, _us_outputs, _adc_inputs
    
    if nombre_placa not in PIN_MAPS:
        print(f"Error: Placa '{nombre_placa}' no válida. Usando N_ESP32 por defecto.")
        nombre_placa = "N_ESP32"
        
    _placa_actual = nombre_placa
    PINS = PIN_MAPS[_placa_actual]
    
    # Inicializar salidas y apagar por seguridad
    _digital_outputs = [Pin(p, Pin.OUT) for p in PINS['digital_outputs']]
    for pin in _digital_outputs:
        pin.value(0)
        
    _digital_inputs = [Pin(p, Pin.IN, Pin.PULL_DOWN) for p in PINS['digital_inputs']]
    _us_outputs = [Pin(p, Pin.IN, Pin.PULL_DOWN) for p in PINS['us_outputs']]
    
    # Inicializar ADCs
    _adc_inputs = []
    for p in PINS['adc_inputs']:
        adc = ADC(Pin(p))
        adc.atten(ADC.ATTN_11DB) # Rango de 0 a 3.3V
        _adc_inputs.append(adc)
    '''
    for p in PINS['servo_pins']:
        adc = ADC(Pin(p))
        adc.atten(ADC.ATTN_11DB) # Rango de 0 a 3.3V
        _adc_inputs.append(adc)
    '''   
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
        elif _placa_actual == "N_ESP32":
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
        elif _placa_actual == "N_ESP32":
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
