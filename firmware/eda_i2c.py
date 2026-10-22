# -*- coding: utf-8 -*-
"""
Módulo Interno I2C (eda_i2c.py)
Gestiona la comunicación con Pantallas LCD y Teclados Matriciales I2C.

"""

import utime
import math
from machine import Pin, I2C

# ======================================================================
# --- 1. CLASES DE HARDWARE (LCD y Teclado) ----------------------------
# ======================================================================

class I2cLcd:
    # Comandos del LCD
    LCD_CLEARDISPLAY = 0x01
    LCD_ENTRYMODESET = 0x04
    LCD_DISPLAYCONTROL = 0x08
    LCD_FUNCTIONSET = 0x20
    LCD_SETDDRAMADDR = 0x80

    # Flags
    LCD_ENTRYLEFT = 0x02
    LCD_ENTRYSHIFTDECREMENT = 0x00
    LCD_DISPLAYON = 0x04
    LCD_CURSOROFF = 0x00
    LCD_BLINKOFF = 0x00
    LCD_4BITMODE = 0x00
    LCD_2LINE = 0x08
    LCD_5x8DOTS = 0x00

    # Pines mochila PCF8574
    LCD_BACKLIGHT = 0x08  
    LCD_NOBACKLIGHT = 0x00
    ENABLE = 0x04         

    def __init__(self, i2c, addr, cols=16, rows=2):
        self.i2c = i2c
        self.addr = addr
        self.cols = cols
        self.rows = rows
        self.backlight_val = self.LCD_BACKLIGHT

        utime.sleep_ms(50)
        self.write_nibble(0x30)
        utime.sleep_ms(5)
        self.write_nibble(0x30)
        utime.sleep_ms(1)
        self.write_nibble(0x30)
        utime.sleep_ms(1)
        self.write_nibble(0x20)

        self.write_command(self.LCD_FUNCTIONSET | self.LCD_4BITMODE | self.LCD_2LINE | self.LCD_5x8DOTS)
        self.write_command(self.LCD_DISPLAYCONTROL | self.LCD_DISPLAYON | self.LCD_CURSOROFF | self.LCD_BLINKOFF)
        self.write_command(self.LCD_ENTRYMODESET | self.LCD_ENTRYLEFT | self.LCD_ENTRYSHIFTDECREMENT)
        self.clear()

    def write_nibble(self, nibble):
        byte = (nibble & 0xF0) | self.backlight_val
        self.i2c.writeto(self.addr, bytearray([byte | self.ENABLE]))
        utime.sleep_us(1)
        self.i2c.writeto(self.addr, bytearray([byte & ~self.ENABLE]))
        utime.sleep_us(50)

    def write_command(self, cmd):
        self.write_nibble(cmd)
        self.write_nibble(cmd << 4)
        if cmd == self.LCD_CLEARDISPLAY:
            utime.sleep_ms(2)

    def write_data(self, data):
        RS_MASK = 0x01
        high_nibble = data & 0xF0
        low_nibble = (data << 4) & 0xF0
        
        byte = high_nibble | self.backlight_val | RS_MASK
        self.i2c.writeto(self.addr, bytearray([byte | self.ENABLE]))
        utime.sleep_us(1)
        self.i2c.writeto(self.addr, bytearray([byte & ~self.ENABLE]))
        utime.sleep_us(1)

        byte = low_nibble | self.backlight_val | RS_MASK
        self.i2c.writeto(self.addr, bytearray([byte | self.ENABLE]))
        utime.sleep_us(1)
        self.i2c.writeto(self.addr, bytearray([byte & ~self.ENABLE]))
        utime.sleep_us(50)

    def clear(self):
        self.write_command(self.LCD_CLEARDISPLAY)

    def move_to(self, col, row):
        row_offsets = [0x00, 0x40]
        row = max(0, min(self.rows - 1, row))
        self.write_command(self.LCD_SETDDRAMADDR | (col + row_offsets[row]))

    def backlight_on(self):
        self.backlight_val = self.LCD_BACKLIGHT
        self.write_command(0) 

    def backlight_off(self):
        self.backlight_val = self.LCD_NOBACKLIGHT
        self.write_command(0) 

    def putchar(self, char):
        self.write_data(ord(char))


class I2cKeypad:
    def __init__(self, i2c, addr, num_columnas=3):
        self.i2c = i2c
        self.addr = addr
        self.num_columnas = num_columnas 
        
        if self.num_columnas == 3:
            self.teclas = [['1','2','3'], ['4','5','6'], ['7','8','9'], ['*','0','#']]
        else:
            self.teclas = [['1','2','3','A'], ['4','5','6','B'], ['7','8','9','C'], ['*','0','#','D']]

    def leer_tecla(self):
        for i in range(4):
            byte_salida = ~(1 << (i + 4)) & 0xF0
            byte_salida |= 0x07 if self.num_columnas == 3 else 0x0F
            
            try:
                self.i2c.writeto(self.addr, bytearray([byte_salida]))
                lectura = self.i2c.readfrom(self.addr, 1)[0]
                
                for j in range(self.num_columnas):
                    if not (lectura & (1 << j)):
                        return self.teclas[i][j]
            except:
                return None
        return None

class SSD1306_I2C:
    """
    Driver para OLED SSD1306 128x64 (o 128x32) por I2C.
    Sin dependencias externas — todo incluido en esta clase.

    Uso típico:
        oled = SSD1306_I2C(i2c, addr=0x3C)
        oled.fill(0)
        oled.text("Hola!", 0, 0)
        oled.show()
    """

    # Mapa de fuente 8x8, ASCII 32–127
    # Cada entrada es una lista de 8 bytes (columnas).
    _FONT = {
        ' ': [0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00],
        '!': [0x00,0x00,0x5F,0x00,0x00,0x00,0x00,0x00],
        '"': [0x00,0x07,0x00,0x07,0x00,0x00,0x00,0x00],
        '#': [0x14,0x7F,0x14,0x7F,0x14,0x00,0x00,0x00],
        '$': [0x24,0x2A,0x7F,0x2A,0x12,0x00,0x00,0x00],
        '%': [0x23,0x13,0x08,0x64,0x62,0x00,0x00,0x00],
        '&': [0x36,0x49,0x55,0x22,0x50,0x00,0x00,0x00],
        "'": [0x00,0x05,0x03,0x00,0x00,0x00,0x00,0x00],
        '(': [0x00,0x1C,0x22,0x41,0x00,0x00,0x00,0x00],
        ')': [0x00,0x41,0x22,0x1C,0x00,0x00,0x00,0x00],
        '*': [0x14,0x08,0x3E,0x08,0x14,0x00,0x00,0x00],
        '+': [0x08,0x08,0x3E,0x08,0x08,0x00,0x00,0x00],
        ',': [0x00,0x50,0x30,0x00,0x00,0x00,0x00,0x00],
        '-': [0x08,0x08,0x08,0x08,0x08,0x00,0x00,0x00],
        '.': [0x00,0x60,0x60,0x00,0x00,0x00,0x00,0x00],
        '/': [0x20,0x10,0x08,0x04,0x02,0x00,0x00,0x00],
        '0': [0x3E,0x51,0x49,0x45,0x3E,0x00,0x00,0x00],
        '1': [0x00,0x42,0x7F,0x40,0x00,0x00,0x00,0x00],
        '2': [0x72,0x49,0x49,0x49,0x46,0x00,0x00,0x00],
        '3': [0x21,0x41,0x49,0x4D,0x33,0x00,0x00,0x00],
        '4': [0x18,0x14,0x12,0x7F,0x10,0x00,0x00,0x00],
        '5': [0x27,0x45,0x45,0x45,0x39,0x00,0x00,0x00],
        '6': [0x3C,0x4A,0x49,0x49,0x31,0x00,0x00,0x00],
        '7': [0x41,0x21,0x11,0x09,0x07,0x00,0x00,0x00],
        '8': [0x36,0x49,0x49,0x49,0x36,0x00,0x00,0x00],
        '9': [0x46,0x49,0x49,0x29,0x1E,0x00,0x00,0x00],
        ':': [0x00,0x36,0x36,0x00,0x00,0x00,0x00,0x00],
        ';': [0x00,0x56,0x36,0x00,0x00,0x00,0x00,0x00],
        '<': [0x08,0x14,0x22,0x41,0x00,0x00,0x00,0x00],
        '=': [0x14,0x14,0x14,0x14,0x14,0x00,0x00,0x00],
        '>': [0x00,0x41,0x22,0x14,0x08,0x00,0x00,0x00],
        '?': [0x02,0x01,0x51,0x09,0x06,0x00,0x00,0x00],
        '@': [0x32,0x49,0x79,0x41,0x3E,0x00,0x00,0x00],
        'A': [0x7E,0x11,0x11,0x11,0x7E,0x00,0x00,0x00],
        'B': [0x7F,0x49,0x49,0x49,0x36,0x00,0x00,0x00],
        'C': [0x3E,0x41,0x41,0x41,0x22,0x00,0x00,0x00],
        'D': [0x7F,0x41,0x41,0x22,0x1C,0x00,0x00,0x00],
        'E': [0x7F,0x49,0x49,0x49,0x41,0x00,0x00,0x00],
        'F': [0x7F,0x09,0x09,0x09,0x01,0x00,0x00,0x00],
        'G': [0x3E,0x41,0x49,0x49,0x7A,0x00,0x00,0x00],
        'H': [0x7F,0x08,0x08,0x08,0x7F,0x00,0x00,0x00],
        'I': [0x00,0x41,0x7F,0x41,0x00,0x00,0x00,0x00],
        'J': [0x20,0x40,0x41,0x3F,0x01,0x00,0x00,0x00],
        'K': [0x7F,0x08,0x14,0x22,0x41,0x00,0x00,0x00],
        'L': [0x7F,0x40,0x40,0x40,0x40,0x00,0x00,0x00],
        'M': [0x7F,0x02,0x0C,0x02,0x7F,0x00,0x00,0x00],
        'N': [0x7F,0x04,0x08,0x10,0x7F,0x00,0x00,0x00],
        'O': [0x3E,0x41,0x41,0x41,0x3E,0x00,0x00,0x00],
        'P': [0x7F,0x09,0x09,0x09,0x06,0x00,0x00,0x00],
        'Q': [0x3E,0x41,0x51,0x21,0x5E,0x00,0x00,0x00],
        'R': [0x7F,0x09,0x19,0x29,0x46,0x00,0x00,0x00],
        'S': [0x46,0x49,0x49,0x49,0x31,0x00,0x00,0x00],
        'T': [0x01,0x01,0x7F,0x01,0x01,0x00,0x00,0x00],
        'U': [0x3F,0x40,0x40,0x40,0x3F,0x00,0x00,0x00],
        'V': [0x1F,0x20,0x40,0x20,0x1F,0x00,0x00,0x00],
        'W': [0x3F,0x40,0x38,0x40,0x3F,0x00,0x00,0x00],
        'X': [0x63,0x14,0x08,0x14,0x63,0x00,0x00,0x00],
        'Y': [0x07,0x08,0x70,0x08,0x07,0x00,0x00,0x00],
        'Z': [0x61,0x51,0x49,0x45,0x43,0x00,0x00,0x00],
        '[': [0x00,0x7F,0x41,0x41,0x00,0x00,0x00,0x00],
        '\\': [0x02,0x04,0x08,0x10,0x20,0x00,0x00,0x00],
        ']': [0x00,0x41,0x41,0x7F,0x00,0x00,0x00,0x00],
        '^': [0x04,0x02,0x01,0x02,0x04,0x00,0x00,0x00],
        '_': [0x40,0x40,0x40,0x40,0x40,0x00,0x00,0x00],
        '`': [0x00,0x01,0x02,0x04,0x00,0x00,0x00,0x00],
        'a': [0x20,0x54,0x54,0x54,0x78,0x00,0x00,0x00],
        'b': [0x7F,0x48,0x44,0x44,0x38,0x00,0x00,0x00],
        'c': [0x38,0x44,0x44,0x44,0x20,0x00,0x00,0x00],
        'd': [0x38,0x44,0x44,0x48,0x7F,0x00,0x00,0x00],
        'e': [0x38,0x54,0x54,0x54,0x18,0x00,0x00,0x00],
        'f': [0x08,0x7E,0x09,0x01,0x02,0x00,0x00,0x00],
        'g': [0x0C,0x52,0x52,0x52,0x3E,0x00,0x00,0x00],
        'h': [0x7F,0x08,0x04,0x04,0x78,0x00,0x00,0x00],
        'i': [0x00,0x44,0x7D,0x40,0x00,0x00,0x00,0x00],
        'j': [0x20,0x40,0x44,0x3D,0x00,0x00,0x00,0x00],
        'k': [0x7F,0x10,0x28,0x44,0x00,0x00,0x00,0x00],
        'l': [0x00,0x41,0x7F,0x40,0x00,0x00,0x00,0x00],
        'm': [0x7C,0x04,0x18,0x04,0x78,0x00,0x00,0x00],
        'n': [0x7C,0x08,0x04,0x04,0x78,0x00,0x00,0x00],
        'o': [0x38,0x44,0x44,0x44,0x38,0x00,0x00,0x00],
        'p': [0x7C,0x14,0x14,0x14,0x08,0x00,0x00,0x00],
        'q': [0x08,0x14,0x14,0x18,0x7C,0x00,0x00,0x00],
        'r': [0x7C,0x08,0x04,0x04,0x08,0x00,0x00,0x00],
        's': [0x48,0x54,0x54,0x54,0x20,0x00,0x00,0x00],
        't': [0x04,0x3F,0x44,0x40,0x20,0x00,0x00,0x00],
        'u': [0x3C,0x40,0x40,0x20,0x7C,0x00,0x00,0x00],
        'v': [0x1C,0x20,0x40,0x20,0x1C,0x00,0x00,0x00],
        'w': [0x3C,0x40,0x30,0x40,0x3C,0x00,0x00,0x00],
        'x': [0x44,0x28,0x10,0x28,0x44,0x00,0x00,0x00],
        'y': [0x0C,0x50,0x50,0x50,0x3C,0x00,0x00,0x00],
        'z': [0x44,0x64,0x54,0x4C,0x44,0x00,0x00,0x00],
        '{': [0x00,0x08,0x36,0x41,0x00,0x00,0x00,0x00],
        '|': [0x00,0x00,0x7F,0x00,0x00,0x00,0x00,0x00],
        '}': [0x00,0x41,0x36,0x08,0x00,0x00,0x00,0x00],
        '~': [0x10,0x08,0x08,0x10,0x08,0x00,0x00,0x00],
    }

    def __init__(self, i2c, addr=0x3C, width=128, height=64):
        self.i2c    = i2c
        self.addr   = addr
        self.width  = width
        self.height = height
        self.pages  = height // 8
        self._buffer = bytearray(width * self.pages)

        # Secuencia de inicialización SSD1306
        for cmd in [
            0xAE,              # Display OFF
            0xD5, 0x80,        # Set display clock divider
            0xA8, height - 1,  # Set multiplex ratio
            0xD3, 0x00,        # Set display offset
            0x40,              # Set start line = 0
            0x8D, 0x14,        # Enable charge pump
            0x20, 0x00,        # Memory addressing mode: horizontal
            0xA1,              # Segment re-map (col 127 = SEG0)
            0xC8,              # COM output scan direction (remapped)
            0xDA, 0x12,        # COM pins hardware config
            0x81, 0xCF,        # Set contrast
            0xD9, 0xF1,        # Set pre-charge period
            0xDB, 0x40,        # Set VCOMH deselect level
            0xA4,              # Display from RAM (not all on)
            0xA6,              # Normal display (not inverted)
            0xAF,              # Display ON
        ]:
            self._cmd(cmd)

    def _cmd(self, cmd):
        """Envía un byte de comando al SSD1306."""
        self.i2c.writeto(self.addr, bytearray([0x00, cmd]))

    # ------------------------------------------------------------------
    # Volcado a pantalla
    # ------------------------------------------------------------------

    def show(self):
        """Vuelca el buffer interno al display. Llamar después de dibujar."""
        self._cmd(0x21); self._cmd(0);              self._cmd(self.width - 1)
        self._cmd(0x22); self._cmd(0);              self._cmd(self.pages - 1)
        buf    = bytearray(1 + len(self._buffer))
        buf[0] = 0x40
        buf[1:] = self._buffer
        self.i2c.writeto(self.addr, buf)

    # ------------------------------------------------------------------
    # Dibujo básico
    # ------------------------------------------------------------------

    def fill(self, color):
        """Rellena toda la pantalla de forma instantánea."""
        v = b'\xff' if color else b'\x00'
        # Magia de Python: Asignación masiva en C (ultra rápido)
        self._buffer[:] = v * len(self._buffer)

    def fill_rect(self, x, y, w, h, color=1):
        """Rectángulo relleno ultra-rápido (Acceso directo a memoria de bytes)."""
        # 1. Recorte de bordes por seguridad
        if x < 0: w += x; x = 0
        if y < 0: h += y; y = 0
        if w <= 0 or h <= 0 or x >= self.width or y >= self.height: return
        if x + w > self.width: w = self.width - x
        if y + h > self.height: h = self.height - y

        # 2. Calculamos las "páginas" (filas de 8 píxeles de alto) que ocupa
        y0 = y
        y1 = y + h - 1
        page0 = y0 // 8
        page1 = y1 // 8

        # 3. Dibujamos manipulando bytes completos (8 píxeles a la vez)
        for page in range(page0, page1 + 1):
            mask = 0xFF
            if page == page0:
                mask &= ((0xFF << (y0 % 8)) & 0xFF)
            if page == page1:
                mask &= ((0xFF >> (7 - (y1 % 8))) & 0xFF)
            
            offset = page * self.width + x
            
            if color:
                for i in range(w):
                    self._buffer[offset + i] |= mask
            else:
                inv_mask = (~mask) & 0xFF
                for i in range(w):
                    self._buffer[offset + i] &= inv_mask

    def pixel(self, x, y, color=1):
        """Enciende o apaga un píxel. color: 1=encendido, 0=apagado."""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        page = y // 8
        bit  = y % 8
        idx  = x + page * self.width
        if color:
            self._buffer[idx] |=  (1 << bit)
        else:
            self._buffer[idx] &= ~(1 << bit)

    def hline(self, x, y, w, color=1):
        """Línea horizontal."""
        for i in range(w):
            self.pixel(x + i, y, color)

    def vline(self, x, y, h, color=1):
        """Línea vertical."""
        for i in range(h):
            self.pixel(x, y + i, color)

    def line(self, x0, y0, x1, y1, color=1):
        """Línea entre dos puntos (algoritmo de Bresenham)."""
        dx =  abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.pixel(x0, y0, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy; x0 += sx
            if e2 <= dx:
                err += dx; y0 += sy

    def rect(self, x, y, w, h, color=1):
        """Rectángulo vacío."""
        self.hline(x,     y,     w, color)
        self.hline(x,     y+h-1, w, color)
        self.vline(x,     y,     h, color)
        self.vline(x+w-1, y,     h, color)


    def circle(self, cx, cy, r, color=1):
        """Círculo vacío (algoritmo de punto medio)."""
        x, y, err = r, 0, 1 - r
        while x >= y:
            for pts in [(cx+x,cy+y),(cx-x,cy+y),(cx+x,cy-y),(cx-x,cy-y),
                        (cx+y,cy+x),(cx-y,cy+x),(cx+y,cy-x),(cx-y,cy-x)]:
                self.pixel(pts[0], pts[1], color)
            y += 1
            if err < 0:
                err += 2 * y + 1
            else:
                x -= 1; err += 2 * (y - x) + 1

    # ------------------------------------------------------------------
    # Texto
    # ------------------------------------------------------------------

    def text(self, s, x, y, color=1):
        """
        Escribe una cadena con fuente 8x8.
        Cada carácter ocupa 8 píxeles de ancho y 8 de alto.
        Los caracteres no reconocidos se omiten.
        """
        for char in str(s):
            cols = self._FONT.get(char)
            if cols is None:
                x += 8
                continue
            for col_idx, col_data in enumerate(cols):
                for row_idx in range(8):
                    if col_data & (1 << row_idx):
                        self.pixel(x + col_idx, y + row_idx, color)
            x += 8

    # ------------------------------------------------------------------
    # Control de pantalla
    # ------------------------------------------------------------------

    def poweroff(self):
        """Apaga el display (bajo consumo)."""
        self._cmd(0xAE)

    def poweron(self):
        """Enciende el display."""
        self._cmd(0xAF)

    def contrast(self, value):
        """Ajusta el contraste. value: 0–255."""
        self._cmd(0x81)
        self._cmd(max(0, min(255, value)))

    def invert(self, invert):
        """Invierte los colores. invert: True/False."""
        self._cmd(0xA7 if invert else 0xA6)

# ======================================================================
# --- 2. GESTIÓN Y ESTADO DEL BUS I2C ----------------------------------
# ======================================================================
bus_i2c = None
lcds = {}
keypads = {}
oled_display = None # <--- Nueva variable de estado para el OLED

HEX_TO_LCD_ID = {
    0x27: 101, 0x26: 102, 0x25: 103, 0x24: 104, 0x23: 105, 0x22: 106, 0x21: 107, 0x20: 108,
    0x3F: 101, 0x3E: 102, 0x3D: 103, 0x3C: 104, 0x3B: 105, 0x3A: 106, 0x39: 107, 0x38: 108
}

HEX_TO_KPD_ID = {
    0x20: 208, 0x21: 207, 0x22: 206, 0x23: 205, 0x24: 204, 0x25: 203, 0x26: 202, 0x27: 201,
    0x38: 208, 0x39: 207, 0x3A: 206, 0x3B: 205, 0x3C: 204, 0x3D: 203, 0x3E: 202, 0x3F: 201
}

def inicializar_bus(pines_i2c: tuple) -> bool:
    global bus_i2c, lcds, keypads, oled_display
    
    try:
        bus_i2c = I2C(0, scl=Pin(pines_i2c[0]), sda=Pin(pines_i2c[1]), freq=400000)
        dispositivos = bus_i2c.scan()
        
        if not dispositivos:
            print("I2C: Bus activo, pero no se detectaron pantallas ni teclados.")
            return True
            
        print(f"I2C: Direcciones encontradas: {[hex(d) for d in dispositivos]}")
        
        for addr in dispositivos:
            
            # --- 1. PRIMERO BUSCAMOS EL OLED (Prioridad absoluta) ---
            if addr in (0x3C, 0x3D):
                try:
                    oled_display = SSD1306_I2C(bus_i2c, addr, 128, 64)
                    oled_display.fill(0)
                    oled_display.show()
                    print(f" -> OLED asignado (Dirección: {hex(addr)})")
                except Exception as e:
                    print(f"Error al inicializar OLED: {e}")
                    
            # --- 2. LUEGO BUSCAMOS PANTALLAS LCD ---
            elif addr in HEX_TO_LCD_ID:
                lcd_id = HEX_TO_LCD_ID[addr]
                lcds[lcd_id] = I2cLcd(bus_i2c, addr, 16, 2)
                lcds[lcd_id].backlight_on()
                print(f" -> LCD asignado al ID: {lcd_id}")
                
            # --- 3. POR ÚLTIMO TECLADOS MATRICIALES ---
            elif addr in HEX_TO_KPD_ID:
                kpd_id = HEX_TO_KPD_ID[addr]
                keypads[kpd_id] = I2cKeypad(bus_i2c, addr, num_columnas=3)
                print(f" -> Teclado asignado al ID: {kpd_id}")
                
        return True
    except Exception as e:
        print(f"Error crítico al inicializar I2C: {e}")
        return False


# ======================================================================
# --- 3. FUNCIONES DE EJECUCIÓN (Llamadas por la Fachada) --------------
# ======================================================================

def _obtener_lcds(direccion: int) -> list:
    """Resuelve si el comando va a un ID específico o a todos (Broadcast)."""
    if direccion in lcds:
        return [lcds[direccion]]
    if direccion is None:
        return list(lcds.values())
    return []

def escribir_lcd(col: int, fil: int, texto: str, direccion: int = None):
    for lcd in _obtener_lcds(direccion):
        c, f = col - 1, fil - 1
        lcd.move_to(c, f)
        for char in texto:
            if c > 15: # Lógica simple de salto de línea
                if f == 0:
                    f = 1
                    c = 0
                    lcd.move_to(c, f)
                else:
                    break
            lcd.putchar(char) 
            c += 1

def limpiar_lcd(direccion: int = None):
    for lcd in _obtener_lcds(direccion):
        lcd.clear()

def controlar_luz(estado: bool, direccion: int = None):
    for lcd in _obtener_lcds(direccion):
        if estado:
            lcd.backlight_on()
        else:
            lcd.backlight_off()

def limpiar_todo():
    """Limpia y enciende la luz de todas las pantallas registradas (Uso al detener)."""
    for lcd in lcds.values():
        lcd.clear()
        lcd.backlight_on()

def leer_tecla(id_teclado: int = None) -> str:
    if not keypads:
        return None
    if id_teclado is None:
        return list(keypads.values())[0].leer_tecla()
    if id_teclado in keypads:
        return keypads[id_teclado].leer_tecla()
    return None


    
# ----------------------------------------------------------------------
# --- 4. FUNCIONES DEL DISPLAY OLED -----------------------------------
# ----------------------------------------------------------------------

def oled_print(columna, fila, txt, escala):
    if oled_display is None: return
    x0, y0 = columna * 8 * escala, fila * 8 * escala
    if escala == 1:
        oled_display.text(str(txt), x0, y0)
        return
    for char in str(txt):
        cols = SSD1306_I2C._FONT.get(char)
        if cols is None:
            x0 += 8 * escala
            continue
        for col_idx, col_data in enumerate(cols):
            for row_idx in range(8):
                if col_data & (1 << row_idx):
                    for sc in range(escala):
                        for sr in range(escala):
                            px, py = x0 + col_idx * escala + sc, y0 + row_idx * escala + sr
                            if 0 <= px < oled_display.width and 0 <= py < oled_display.height:
                                oled_display._buffer[px + (py // 8) * oled_display.width] |= (1 << (py % 8))
        x0 += 8 * escala

def oled_mostrar():
    if oled_display is None: return
    oled_display.show()

def oled_limpiar():
    if oled_display: 
        oled_display.fill(0)
        oled_display.show()

def oled_luz(estado):
    if oled_display: 
        oled_display.poweron() if estado else oled_display.poweroff()

def oled_invertir(estado):
    if oled_display: oled_display.invert(estado)

def oled_contraste(valor):
    if oled_display: oled_display.contrast(int(valor))

def oled_pixel(x, y, color):
    if oled_display: oled_display.pixel(x, y, color)

def oled_linea(x0, y0, x1, y1):
    if oled_display: oled_display.line(x0, y0, x1, y1)

def oled_circulo(cx, cy, radio):
    if oled_display: oled_display.circle(cx, cy, radio)

def oled_rect(x, y, ancho, alto, relleno):
    if oled_display:
        oled_display.fill_rect(x, y, ancho, alto) if relleno else oled_display.rect(x, y, ancho, alto)

def oled_borrar_memoria():
    global oled_display
    if oled_display is not None:
        oled_display.fill(0)
    
# ======================================================================
# --- 8b. GRÁFICOS ESPECIALES PARA PROYECTOS (VALORES PUROS 0-100) ----
# ======================================================================
_historial_sismografo = []
def borrarOLED():
    """Limpia el buffer interno en memoria sin apagar la pantalla física."""
    global oled
    if oled is not None:
        oled.fill(0)

def dibujarPerilla(x_centro, y_centro, radio, valor):
    """Dibuja una perilla circular. Recibe valores puros de 0 a 100."""
    pasos = 12
    for i in range(pasos):
        a1 = math.radians(i * (360 / pasos))
        a2 = math.radians((i + 1) * (360 / pasos))
        x1 = int(x_centro + radio * math.cos(a1))
        y1 = int(y_centro + radio * math.sin(a1))
        x2 = int(x_centro + radio * math.cos(a2))
        y2 = int(y_centro + radio * math.sin(a2))
        oled_linea(x1, y1, x2, y2)
    
    # Limita el valor por seguridad antes de calcular el ángulo
    val_filtrado = max(0, min(valor, 100))
    angulo_grados = 135 + (val_filtrado * 2.7)
    angulo_rad = math.radians(angulo_grados)
    x_linea = int(x_centro + (radio - 3) * math.cos(angulo_rad))
    y_linea = int(y_centro + (radio - 3) * math.sin(angulo_rad))
    oled_linea(x_centro, y_centro, x_linea, y_linea)

def dibujarVUMetro(valor):
    """Dibuja un vúmetro analógico de aguja. Recibe valores puros de 0 a 100."""
    x_centro, y_centro, radio = 64, 58, 40
    for i in range(18):
        a1 = math.radians(180 + i * 10)
        a2 = math.radians(180 + (i + 1) * 10)
        x1 = int(x_centro + radio * math.cos(a1))
        y1 = int(y_centro + radio * math.sin(a1))
        x2 = int(x_centro + radio * math.cos(a2))
        y2 = int(y_centro + radio * math.sin(a2))
        oled_linea(x1, y1, x2, y2)
        
    for pct in [0, 25, 50, 75, 100]:
        angulo_tick = math.radians(180 + pct * 1.8)
        x_inicio = int(x_centro + radio * math.cos(angulo_tick))
        y_inicio = int(y_centro + radio * math.sin(angulo_tick))
        x_fin = int(x_centro + (radio + 4) * math.cos(angulo_tick))
        y_fin = int(y_centro + (radio + 4) * math.sin(angulo_tick))
        oled_linea(x_inicio, y_inicio, x_fin, y_fin)

    val_filtrado = max(0, min(valor, 100))
    angulo_aguja = math.radians(180 + val_filtrado * 1.8)
    x_aguja = int(x_centro + (radio - 2) * math.cos(angulo_aguja))
    y_aguja = int(y_centro + (radio - 2) * math.sin(angulo_aguja))
    oled_linea(x_centro, y_centro, x_aguja, y_aguja)
    oled_rect(x_centro - 3, y_centro - 2, 7, 3, relleno=True)

def dibujarEcualizador(b1=None, b2=None, b3=None, b4=None):
    """
    Dibuja un ecualizador dinámico. Muestra solo las barras que reciban valor.
    Adapta el ancho automáticamente. 
    Altura corregida para proteger la zona azul (evita que se pinte de amarillo al 100%).
    """
    # 1. Filtramos y nos quedamos solo con los canales que NO sean None
    entradas_recibidas = [v for v in [b1, b2, b3, b4] if v is not None]
    cantidad_barras = len(entradas_recibidas)
    
    if cantidad_barras == 0:
        return

    # 2. Configuración física de la pantalla OLED (Zona Azul Protegida)
    ancho_pantalla = 128
    y_piso = 55
    alto_maximo = 32   # <--- CORREGIDO: Bajamos de 45 a 32 para que no toque la zona amarilla
    espacio_entre = 8  # Separación fija entre las barras

    # 3. MATEMÁTICA DINÁMICA: Calculamos el ancho ideal según la cantidad de barras
    ancho_disponible = ancho_pantalla - (espacio_entre * (cantidad_barras + 1))
    ancho_barra = ancho_disponible // cantidad_barras
    
    # Calculamos el margen izquierdo inicial para centrar el bloque completo
    ancho_total_bloque = (ancho_barra * cantidad_barras) + (espacio_entre * (cantidad_barras - 1))
    margen_izquierdo = (ancho_pantalla - ancho_total_bloque) // 2

    # 4. DIBUJAR LAS BARRAS ACTIVAS
    for i in range(cantidad_barras):
        x_pos = margen_izquierdo + i * (ancho_barra + espacio_entre)
        
        # Filtramos el valor entre 0 y 100 por seguridad
        val_filtrado = max(0, min(entradas_recibidas[i], 100))
        
        # Calculamos la altura en píxeles basándonos en el nuevo tope seguro
        altura_pixeles = int((val_filtrado / 100) * alto_maximo)
        
        # Dibujamos por "ladrillos" de 4 píxeles de alto para adaptarlo a la nueva escala
        num_ladrillos = altura_pixeles // 4
        for j in range(num_ladrillos):
            y_ladrillo = y_piso - (j * 4)
            oled_rect(x_pos, y_ladrillo, ancho_barra, 2, relleno=True)
            
        # Dibujamos la línea de piso exacta para esta barra
        oled_linea(x_pos, y_piso + 3, x_pos + ancho_barra, y_piso + 3)
        
        
def dibujarTanqueVertical(valor):
    """Dibuja un tanque vertical fijo en zona azul. Recibe valores puros de 0 a 100."""
    x_tanque = 54
    y_tanque = 22
    ancho_tanque = 20
    alto_tanque = 38
    
    oled_rect(x_tanque, y_tanque, ancho_tanque, alto_tanque, relleno=False)
    y_piso = y_tanque + alto_tanque
    y_mitad = y_tanque + (alto_tanque // 2)
    
    oled_linea(x_tanque - 5, y_tanque, x_tanque - 2, y_tanque)
    oled_linea(x_tanque - 5, y_mitad, x_tanque - 2, y_mitad)
    oled_linea(x_tanque - 5, y_piso, x_tanque - 2, y_piso)

    val_filtrado = max(0, min(valor, 100))
    altura_relleno = int((val_filtrado / 100) * alto_tanque)
    if altura_relleno > 0:
        y_inicio_relleno = y_piso - altura_relleno
        oled_rect(x_tanque + 2, y_inicio_relleno + 1, ancho_tanque - 4, altura_relleno - 1, relleno=True)

def dibujarRobot(emocion):
    """Dibuja la cara animada de un robot según su emoción ('enojado', 'feliz', 'loco')."""
    oled_rect(24, 4, 80, 56, relleno=False)
    oled_rect(19, 24, 5, 16, relleno=True)
    oled_rect(104, 24, 5, 16, relleno=True)
    if emocion == "enojado":
        oled_linea(40, 20, 52, 28)
        oled_linea(88, 20, 76, 28)
        oled_linea(54, 48, 64, 42)
        oled_linea(64, 42, 74, 48)
    elif emocion == "feliz":
        oled_rect(42, 20, 10, 10, relleno=True)
        oled_rect(76, 20, 10, 10, relleno=True)
        oled_linea(48, 42, 54, 48)
        oled_linea(54, 48, 74, 48)
        oled_linea(74, 48, 80, 42)
    elif emocion == "loco":
        oled_rect(38, 16, 16, 16, relleno=False)
        oled_rect(74, 16, 16, 16, relleno=False)
        oled_rect(44, 22, 4, 4, relleno=True)
        oled_rect(80, 22, 4, 4, relleno=True)
        oled_rect(56, 40, 16, 12, relleno=False)


_historial_sismografo = []
def dibujarSismografo(valor, velocidad=1):
    global _historial_sismografo
    
    # 1. Calculamos la posición Y del valor (0 a 100)
    val_filtrado = max(0, min(valor, 100))
    y_mapeado = int(62 - (val_filtrado / 100) * 40)
    
    # 2. Validación robusta de la velocidad (por defecto 1, máximo 10)
    vel = 1
    if isinstance(velocidad, (int, float)):
        vel = int(max(1, min(velocidad, 10)))
        
    # 3. "Arrastramos" el lápiz 'vel' píxeles hacia la derecha de golpe
    for _ in range(vel):
        _historial_sismografo.append(y_mapeado)
        
    # 4. Mantenemos el historial dentro de los 128 píxeles del OLED
    while len(_historial_sismografo) > 128:
        _historial_sismografo.pop(0)
        
    # 5. Dibujamos las líneas del gráfico conectando los puntos
    for i in range(len(_historial_sismografo) - 1):
        oled_linea(i, _historial_sismografo[i], i + 1, _historial_sismografo[i + 1])
        
    # 6. Dibujamos la línea de base (punteada) en la zona azul
    for x in range(0, 128, 6):
        oled_pixel(x, 42, 1)
        
    # 7. Mostramos la velocidad en la pantalla (Fila 1, debajo del título)
    oled_print(0, 1, f"Vel: {vel}x", 1)


def dibujarBarraHorizontal(valor):
    """Dibuja una barra de progreso horizontal en la zona azul. Recibe valores de 0 a 100."""
    x_barra = 14          # Margen izquierdo seguro
    y_barra = 36          # Centrado verticalmente en la zona azul
    ancho_maximo = 100    # Largo total de la barra (100 píxeles hace que 1 píxel = 1%)
    alto_barra = 12       # Grosor de la barra
    
    # 1. Dibujamos el contorno exterior de la barra (vacía)
    oled_rect(x_barra, y_barra, ancho_maximo, alto_barra, relleno=False)
    
    # Limitamos el valor por seguridad entre 0 y 100
    val_filtrado = max(0, min(valor, 100))
    
    # 2. Como el ancho máximo es 100, el valor es directamente el ancho del relleno
    if val_filtrado > 0:
        # Dejamos 2 píxeles de margen interno para que se vea estético dentro del contorno
        oled_rect(x_barra + 2, y_barra + 2, val_filtrado - 4, alto_barra - 4, relleno=True)
        
        
# ======================================================================
# --- FUNCIÓN MAESTRA (ORQUESTADOR DE GRÁFICOS OPTIMIZADO) ------------
# ======================================================================

def orquestar_grafico(tipo_grafico, titulo, v1, v2, v3, v4):
    #if oled_display is None: return
    
    MAPEO_GRAFICOS = {
        1: "sismografo",    "sismografo": "sismografo", "sismógrafo": "sismografo",
        2: "tanque",        "tanque": "tanque",
        3: "vumetro",       "vumetro": "vumetro",       "vúmetro": "vumetro",
        4: "perilla",       "perilla": "perilla",
        5: "barra",         "barra": "barra",
        6: "robot_feliz",   "robot_feliz": "robot_feliz",
        7: "robot_enojado", "robot_enojado": "robot_enojado",
        8: "robot_loco",    "robot_loco": "robot_loco",
        9: "ecualizador",   "ecualizador": "ecualizador"
    }
    
    # 2. Convertir / detectar el tipo de gráfico de forma segura
    key = tipo_grafico.lower() if isinstance(tipo_grafico, str) else tipo_grafico
    tipo = MAPEO_GRAFICOS.get(key, None)
    
    if tipo is None:
        print("Error: Gráfico OLED no reconocido.")
        return

    oled_borrar_memoria()
    oled_print(0, 0, f"{titulo.upper()}", 1)
    
    val_individual = v1 if v1 is not None else 0
    if tipo != "ecualizador":
        oled_print(11, 0, f"{val_individual}%", 1)
    
    # 6. Orquestar el dibujo según el tipo validado
    if tipo == "sismografo":
        dibujarSismografo(val_individual,v2)
        
    elif tipo == "tanque":
        dibujarTanqueVertical(val_individual)
        
    elif tipo == "vumetro":
        dibujarVUMetro(val_individual)
        
    elif tipo == "perilla":
        dibujarPerilla(64, 40, 18, val_individual)
        
    elif tipo == "barra":
        dibujarBarraHorizontal(val_individual)
        
    elif tipo == "robot_feliz":
        dibujarRobot("feliz")
        
    elif tipo == "robot_enojado":
        dibujarRobot("enojado")
        
    elif tipo == "robot_loco":
        dibujarRobot("loco")
        
    elif tipo == "ecualizador":
        dibujarEcualizador(v1, v2, v3, v4)
        
    # 7. Refrescar y mandar el diseño a la pantalla física
    oled_mostrar()
    

    
    
