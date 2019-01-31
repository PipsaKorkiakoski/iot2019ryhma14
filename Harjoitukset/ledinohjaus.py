import RPi.GPIO as GPIO # get needed Python libs
import time
#pin def
ledPin = 20 # Broadcom pin 18 (P1 pin 12)
# Pin Setup:
GPIO.setmode(GPIO.BCM) # Broadcom pin-numbering scheme
GPIO.setup(ledPin, GPIO.OUT) # LED pin set as output
GPIO.output(ledPin, GPIO.HIGH) # Led shines
time.sleep(2) # two seconds
GPIO.cleanup()