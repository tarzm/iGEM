import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(12, GPIO.OUT)

try:
    while True:
        # set GPIO12 pin to HIGH
        GPIO.output(12, GPIO.HIGH)
        print("fan is ON")
        time.sleep(20)

        # set GPIO12 pin to LOW
        GPIO.output(12, GPIO.LOW)
        print("fan is OFF")
        time.sleep(20)
except KeyboardInterrupt:
    pass
finally:
    GPIO.output(12, GPIO.LOW)
    GPIO.cleanup()
