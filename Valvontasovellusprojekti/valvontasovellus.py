import RPi.GPIO as GPIO
import io
import picamera
import logging
import socketserver
from threading import Condition
from http import server
import os
import time
import queue
import threading
import mysql.connector
os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')
temp_sensor = "/sys/bus/w1/devices/22-0000005740da/w1_slave"

lampotila = 0
halyraja = 23
ledPin = 12
halytys = False
GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)
GPIO.setup(ledPin, GPIO.OUT)
GPIO.setup(11, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
db = mysql.connector.connect(host="localhost",
                     user="username",
                     passwd="passwd",
                     db="database")

cur = db.cursor()

def button_detector():
    while True:
        if GPIO.input(11) == True:
            buttonq.put(True)
            print("Nappi painettu")
            time.sleep(1)
            
def led_blinker():
    while True:
        t = threading.currentThread()
        while getattr(t, "do_run", True):
            GPIO.output(ledPin, GPIO.HIGH)
            time.sleep(0.2) 
            GPIO.output(ledPin, GPIO.LOW)
            time.sleep(0.2)

buttonq = queue.Queue()
buttont = threading.Thread(target=button_detector)
buttont.start()

blinkert = threading.Thread(target=led_blinker)
blinkert.do_run = False
blinkert.start()


PAGE="""\
<html>
<head>
<title>picamera MJPEG streaming demo</title>
</head>
<body>
<h1>PiCamera MJPEG Streaming Demo</h1>
<img src="stream.mjpg" width="640" height="480" />

</body>
</html>
"""
def temp_raw():
    f = open(temp_sensor, 'r')
    lines = f.readlines()
    f.close()
    return lines
def read_temp():
    lines = temp_raw()
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = temp_raw()
    temp_output = lines[1].find('t=')
    if temp_output != -1:
        temp_string = lines[1].strip()[temp_output+2:]
        temp_c = float(temp_string) / 1000.0
        temp_f = temp_c * 9.0 / 5.0 + 32.0
        lampotila = temp_c
        print("tietokanta alku")
        #cur.execute("INSERT temperature SET temp = 5 where id = 1")
        cur.execute("UPDATE temperature SET temp = %s where id = 0", (lampotila,))
        print("meneeko")
        db.commit()
        print("meni lapi")
        return lampotila
def tarkista_lampotila(lampotila):    
    if lampotila > halyraja:
        print("Liian kuuma")
        global halytys
        halytys = True
        return True
    else:
        return False
    
 # kamerahommia
 #
 #
class StreamingOutput(object):
    def __init__(self):
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition = Condition()

    def write(self, buf):
        if buf.startswith(b'\xff\xd8'):
            # New frame, copy the existing buffer's content and notify all
            # clients it's available
            self.buffer.truncate()
            with self.condition:
                self.frame = self.buffer.getvalue()
                self.condition.notify_all()
            self.buffer.seek(0)
        return self.buffer.write(buf)

class StreamingHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            content = PAGE.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            
            self.end_headers()
              
            self.wfile.write(content)
        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    global halytys
                    if(halytys == True):
                        print("Haly")
                        blinkert.do_run = True

                    tila = False
                    if(buttonq.empty() == False):
                        tila = buttonq.get_nowait()
                        if tila == True:
                            halytys = False
                            blinkert.do_run = False
                            tila = False
                            GPIO.output(ledPin, GPIO.LOW)
                    lampotila = read_temp()
                    print(lampotila)
                    tarkista_lampotila(lampotila)
                    with output.condition:
                        output.condition.wait()
                        frame = output.frame
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                logging.warning(
                    'Removed streaming client %s: %s',
                    self.client_address, str(e))
        else:
            self.send_error(404)
            self.end_headers()

class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

with picamera.PiCamera(resolution='640x480', framerate=24) as camera:
    output = StreamingOutput()
    camera.start_recording(output, format='mjpeg')
  
    try:
        address = ('', 8000)
        server = StreamingServer(address, StreamingHandler)
        server.serve_forever()
    finally:
        camera.stop_recording()
