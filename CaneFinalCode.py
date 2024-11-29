import os
import math
import time
import busio
import board
import numpy as np
import pygame
from scipy.interpolate import griddata
from colour import Color
import adafruit_amg88xx
import RPi.GPIO as GPIO
import subprocess

# Initialize GPIO for all devices
GPIO.setmode(GPIO.BCM)

# Ultrasonic Sensors GPIO Pins
TRIG1 = 17
ECHO1 = 18
TRIG2 = 22
ECHO2 = 23

# Vibration Motor GPIO Pin
VIBRATOR_PIN = 25

# Setup GPIO for devices
GPIO.setup(VIBRATOR_PIN, GPIO.OUT)
GPIO.setup(TRIG1, GPIO.OUT)
GPIO.setup(ECHO1, GPIO.IN)
GPIO.setup(TRIG2, GPIO.OUT)
GPIO.setup(ECHO2, GPIO.IN)

def distance(TRIG, ECHO):
    GPIO.output(TRIG, False)
    time.sleep(0.0001)  # Reduced sleep time
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)
    start = time.time()
    end = time.time()
    while GPIO.input(ECHO) == 0 and (time.time() - start) < 0.1:
        start = time.time()
    while GPIO.input(ECHO) == 1 and (time.time() - end) < 0.1:
        end = time.time()
    elapsed = end - start
    if elapsed >= 0.1:
        return -1  # Return default value if no valid measurement obtained
    distance = (elapsed * 34300) / 2
    return distance

def activate_vibrator():
    GPIO.output(VIBRATOR_PIN, GPIO.HIGH)

def deactivate_vibrator():
    GPIO.output(VIBRATOR_PIN, GPIO.LOW)

# Function for text-to-speech using espeak
def tts(text):
    subprocess.run(["espeak", text])

# Calculate the horizontal distance between the ultrasonic sensors
height = 4  # Height of the cane in feet
angle = 45  # Angle of the cane in degrees
horizontal_distance = height * math.tan(math.radians(angle))

# Thermal camera and display setup
i2c_bus = busio.I2C(board.SCL, board.SDA)
sensor = adafruit_amg88xx.AMG88XX(i2c_bus)
os.putenv('SDL_FBDEV', '/dev/fb1')
pygame.init()
height, width = 1080, 1920
lcd = pygame.display.set_mode((width, height))
colors = list(Color("indigo").range_to(Color("red"), 1024))
colors = [(int(c.red * 255), int(c.green * 255), int(c.blue * 255)) for c in colors]

object_threshold = 25  # Lower threshold for considering a pixel as part of an object

while True:
    dis1 = distance(TRIG1, ECHO1)
    dis2 = distance(TRIG2, ECHO2)

    if dis1 == -1 or dis2 == -1:
        print("Ultrasonic sensor reading error")
    elif dis1 < 125:
        if dis2 < 200:
            tts("Object detected")
        else:
            tts("Object detected")
    elif dis2 < 50:
        tts("Curb detected")

    # Update the thermal display; adjust threshold for object detection
    pixels = [p for row in sensor.pixels for p in row]
    object_pixels = [p if p > object_threshold else 0 for p in pixels]

    grid_x, grid_y = np.mgrid[0:7:32j, 0:7:32j]
    points = [(math.floor(ix / 8), (ix % 8)) for ix in range(0, 64)]
    bicubic = griddata(points, object_pixels, (grid_x, grid_y), method='cubic')
    for ix, row in enumerate(bicubic):
        for jx, pixel in enumerate(row):
            pygame.draw.rect(lcd, colors[int(np.clip(pixel, 0, 1023))],
                             (ix*30, jx*30, 30, 30))

    # Adjust the threshold for activating the vibration motor
    if any(p > object_threshold for p in object_pixels):
        activate_vibrator()
    else:
        deactivate_vibrator()

    pygame.display.update()

    time.sleep(0.1)

GPIO.cleanup()
