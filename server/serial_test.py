import serial
import threading
import time

PORT = "COM4" # change if needed
BAUD_RATE = 9600
ser = serial.Serial(PORT, BAUD_RATE)

def listen():
    while True:
        data = ser.read(ser.in_waiting)
        if data: print("Recived:", data.decode())
        time.sleep(0.05)

listen_thread = threading.Thread(target=listen, daemon=True)
listen_thread.start()

while True: 
    data = input()
    ser.write(data.encode())
    print("sent:", data)
