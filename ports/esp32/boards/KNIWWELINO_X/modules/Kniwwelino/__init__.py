"""
    Port of the C++ KniwwelinoLib to MicroPython for the KniwwelinoX
    which uses the ESP32 as a base board.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the Lesser General Public License as published
    by the Free Software Foundation, version 3 of the License.

    Author: Christophe Kayser
    Version: v0.1
    License: LGPL v3
"""

from micropython import const
from machine import Pin, Timer
from neopixel import NeoPixel
import framebuf

# import font, adapted from MicroBit board port of MicroPython on GitHub
from Kniwwelino.font import font_pendolino3_5x5_pad3msb

# Constants
RGB_NUM       = const(6)
MATRIX_WIDTH  = const(5)
MATRIX_HEIGHT = const(5)

# Pin definition for KniwwelinoX
MATRIX_PIN  = const(25)
RGB_PIN     = const(26)
BUTTON_A    = const(34)
BUTTON_B    = const(35)
P1          = const(4)
P2          = const(32)
P3          = const(27)
P4          = const(15)
P5          = const(14)
P6          = const(13)
P7          = const(33)

I2C_EXT_SDA = const(22)
I2C_EXT_SCL = const(21)

IMU_ADDRESS    = const(0x80)
IMU_SDA        = const(17)
IMU_SCL        = const(16)
IMU_INTERRUPT1 = const(12)

# Colors
RGB_COLOR_RED   = const(0xFF0000)
RGB_COLOR_GREEN = const(0x00FF00)
RGB_COLOR_BLUE  = const(0x0000FF)
RGB_COLOR_ORANGE= const(0xC93B03)
RGB_COLOR_CYAN  = const(0x00FFFF)

# Icons
ICON_WIFI       = const(0xE0F4B4)
ICON_RING       = const(0xE8C62E)
ICON_CROSS      = const(0x1151151)
ICON_CHECK      = const(0xA880)
ICON_SMILE      = const(0x5022E)
ICON_SAD        = const(0x501D1)
ICON_HEART      = const(0xAAC544)
ICON_PLUS       = const(0x427C84)
ICON_ARROW_DOWN = const(0x4255C4)
ICON_ARROW_UP   = const(0x475484)
ICON_ARROW_RIGHT= const(0x417C44)
ICON_ARROW_LEFT = const(0x447D04)

class Kniwwelino:
    _MAPPING = [[0, 1, 2, 3, 4], [9, 8, 7, 6, 5], [10, 11, 12, 13, 14], [19, 18, 17, 16, 15], [20, 21, 22, 23, 24]]

    def __init__(self):
        # 5x5 Matrix with NeoPixels
        self.rgb_matrix = NeoPixel(Pin(MATRIX_PIN, Pin.OUT), MATRIX_WIDTH * MATRIX_HEIGHT)
        # 6 NeoPixels
        self.rgb_led = NeoPixel(Pin(RGB_PIN, Pin.OUT), RGB_NUM)

        # brightness values over 20 are really inadvisable due to brightness of LEDs (8-255)
        self.led_brightness = 10

        # Framebuffer used to put text on matrix
        #self.matrix_fbuf = framebuf.FrameBuffer(bytearray(MATRIX_HEIGHT * MATRIX_WIDTH * 2 * 2), MATRIX_HEIGHT, MATRIX_WIDTH * 2 + 1, framebuf.RGB565)
        self.matrix_fbuf = framebuf.FrameBuffer(bytearray(MATRIX_HEIGHT * 2), MATRIX_HEIGHT, MATRIX_WIDTH * 2 + 1, framebuf.MONO_HMSB)
        # Timer used as ticker for text scrolling
        self.timer = Timer(0)
        # Variables used for text storage for text on matrix
        self.text_to_write = ""
        self.complete_text = ""
        self.block_matrix_write = False
        self.matrix_color = self.Hexto888(RGB_COLOR_RED)
        self.timer_counter = 0

        # Clear LEDs
        self.rgb_matrix.fill((0,0,0))
        self.rgb_matrix.write()
        self.rgb_led.fill((0,0,0))
        self.rgb_led.write()

        # Define button pins as inputs with pull up resistors
        Pin(BUTTON_A, Pin.IN, Pin.PULL_UP)
        Pin(BUTTON_B, Pin.IN, Pin.PULL_UP)

    def MatrixClear(self):
        """
         Clear content on Matrix and stop text scrolling.
        """
        self.timer.deinit()
        self.rgb_matrix.fill((0,0,0))
        self.rgb_matrix.write()
        self.matrix_fbuf.fill(0)
        self.complete_text = ""
        self.text_to_write = ""

    def MatrixDrawIcon(self, icon):
        """
         Draw icon on Matrix, icon can be int (hex or int)
         or string in form of: '1111100000111110000011111'
         where each 5 bits is one row, left to right, top
         to bottom. When giving less than 25 bits,
         rightmost bit starts at bottom right.
        """
        self.MatrixClear()
        if isinstance(icon, str):
            icon = int(icon, 2)
        if icon < 0:
            icon = 0
        if icon > 0x1ffffff:
            icon = 0x1ffffff
        icon = f'{icon:025b}'
        for i in range(25):
            if icon[i] == '1':
                self.rgb_matrix[Kniwwelino._MAPPING[i//5][i%5]] = self.matrix_color
        self.rgb_matrix.write()

    def MatrixSetPixel(self, x, y, state=1):
        """
         Set Matrix pixel in internal buffer, color defined by MatrixSetColor.
         Needs a RGBWriteLED call to display LEDs.
        """
        if state:
            self.rgb_matrix[Kniwwelino._MAPPING[x][y]] = self.matrix_color
        else:
            self.rgb_matrix[Kniwwelino._MAPPING[x][y]] = (0,0,0)

    def MatrixWritePixel(self, x=None, y=None, state=1):
        """
         Write internal Matrix buffer to LEDs and optionally set single pixel.
        """
        if x != None and y != None:
            self.MatrixSetPixel(x, y, state=state)
        self.rgb_matrix.write()

    def MatrixSetColor(self, color):
        """
         Take a hex color in form of 0xFF00FF or 0xff00ff
         and set it as color for RGB Matrix.
        """
        self.matrix_color = self.Hexto888(color)

    def RGBClear(self):
        """
         Clear content of the 6 RGB leds.
        """
        self.rgb_led.fill((0,0,0))
        self.rgb_led.write()

    def RGBSetLED(self, x, color=RGB_COLOR_RED, state=1):
        """
         Set LED in internal buffer, optionally set color.
         Needs a RGBWriteLED call to display LEDs.
        """
        if state:
            self.rgb_led[x] = self.Hexto888(color)
        else:
            self.rgb_led[x] = (0,0,0)

    def RGBWriteLED(self, x=None, color=RGB_COLOR_RED, state=1):
        """
         Write internal LED buffer to LEDs and optionally set single LED.
        """
        if x != None:
            self.RGBSetLED(x, color=color, state=state)
        self.rgb_led.write()

    def MatrixWriteText(self, text, blocking=False, repeating=False, scroll_speed=200):
        """
         Method to write scrolling text to RGB Matrix.
          test: string to write
          blocking: whether to block the call, defaults to False
          repeating: whether to write text once or indefinitely, defaults to False aka. once
          scroll_speed: interval in milliseconds to scroll text, defaults to 200ms
        """
        text = text.strip()
        text +=  "  "
        self.text_to_write = text
        self.complete_text = ""
        self.timer_counter = 5
        self.matrix_fbuf.fill(0)

        if blocking:
            self.block_matrix_write = True

        if repeating:
            text = text[:-1]
            self.text_to_write = text
            self.complete_text = text
            self.block_matrix_write = False

        self.timer.init(period=scroll_speed, mode=Timer.PERIODIC, callback=self._drawText)

        while self.block_matrix_write:
            pass

    def RGB565to888(self, color):
        """
         Helper to convert RGB565 to RGB888.
         16-bit to 24-bit color.
        """
        color = f'{color:015b}'
        r = int(color[0:5], 2)
        g = int(color[5:11], 2)
        b = int(color[11:16], 2)

        r = (r*527+23) >> 6
        g = (g*259+33) >> 6
        b = (b*527+23) >> 6

        return (r, g, b)

    def RGB888to565(self, color, scaling=True):
        """
         Helper to convert RGB888 to RGB565.
         24-bit to 16-bit color.
        """
        color = f'{color:024b}'
        r = int(color[:8], 2)
        g = int(color[8:16], 2)
        b = int(color[16:24], 2)

        if scaling:
            r = (r*self.matrix_brigthness)//255
            g = (g*self.matrix_brigthness)//255
            b = (b*self.matrix_brigthness)//255

        r = (r & 0b11111000) << 8
        g = (g & 0b11111100) << 3
        b = b >> 3

        return r | g | b

    def Hexto888(self, color, scaling=True):
        """
         Helper to convert hex color 0xFF00FF to
         RGB tuple (255, 0, 255).
        """
        color = f'{color:024b}'
        r = int(color[:8], 2)
        g = int(color[8:16], 2)
        b = int(color[16:24], 2)

        if scaling:
            r = (r*self.led_brightness)//255
            g = (g*self.led_brightness)//255
            b = (b*self.led_brightness)//255

        return (r, g, b)

    def _drawChar(self, char):
        """
         Internal method to convert and display ASCII
         character on 5x5 RGB LED matrix.
        """
        code = ord(char)
        if code < 32 or code > 126:
            code = 32

        for x in range(5):
            vline = font_pendolino3_5x5_pad3msb[((code-32)*5)+x]
            if vline != 0:
                vline = f'{vline:08b}'[3:]
                for y in range(5):
                    if vline[y] == '1':
                        self.matrix_fbuf.pixel(x, y+5, 1)

    def _drawText(self, timer):
        """
         Internal method bound to interrupt timer to
         display and scroll text on 5x5 RGB LED matrix.
        """
        if self.text_to_write != "":
            self.matrix_fbuf.scroll(0,-1)
            self.timer_counter += 1
            if self.timer_counter == 6:
                self.timer_counter = 0
                self._drawChar(self.text_to_write[0])
                self.text_to_write = self.text_to_write[1:]
            self._MatrixShowBuffer()
        elif self.complete_text != "":
            self.text_to_write = self.complete_text
            self._drawText(None)
        else:
            self.timer.deinit()
            self.block_matrix_write = False

    def _MatrixShowBuffer(self):
        """
         Internal method to put buffer from framebuffer onto
         5x5 RGB LED matrix.
        """
        self.rgb_matrix.fill((0,0,0))
        for i in range(25):
            if self.matrix_fbuf.pixel(i%5,i//5):
                self.rgb_matrix[Kniwwelino._MAPPING[i%5][i//5]] = self.matrix_color
        self.rgb_matrix.write()
