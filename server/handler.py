from queue import Empty, Queue
import time
import heapq
import serial
import threading
from typing import Any, List, Tuple, Union
from packet import Packet, Log, LogPriority
from flask_socketio import Namespace


BYTE_SIZE = 8192

DELAY = .05
DELAY_LISTEN = .05
DELAY_SEND = .05
DELAY_HEARTBEAT = 3

SEND_ALLOWED = True

BLOCK_SIZE = 32
f = open("black_box.txt", "w+")
f.close()


class Handler(Namespace):
    """ Handles all communication """

    def init(self, port, baud_rate):
        """ Based on given IP and port, create and connect a socket """

        """ A heapqueue of packets to send """
        self.queue_send: List[Tuple[str, str]] = []
        self.rcvd_data = ""
        
        self.send_thread = threading.Thread(target=self.send, daemon=True)
        self.send_thread.daemon = True
        self.listen_thread = threading.Thread(target=self.listen, daemon=True)
        self.listen_thread.daemon = True
        self.heartbeat_thread = threading.Thread(target=self.heartbeat, daemon=True)
        self.heartbeat_thread.daemon = True
        # This is a queue of arguments to be sent to self.ingest()
        self.ingest_queue = Queue()
        # This thread reads from the ingest queue
        self.ingest_thread = threading.Thread(target=self.ingest_loop, daemon=True)
        self.ingest_thread.daemon = True

        self.conn = None
        self.running = False
        self.start_time = time.time()

        try:
            self.ser = serial.Serial(port, baud_rate)
            self.ser.flushInput()
            self.ser.flushOutput()
            print("Finished connecting")

        except Exception as e:
            print("ERROR:", e)
            self.running = False
        
        self.general_copy = None
        self.sensors_copy = None
        self.valves_copy = None
        self.buttons_copy = None

    ## telemetry methods
        
    def begin(self):
        """ Starts the send and listen threads """
        self.running = True
        self.listen_thread.start()
        self.heartbeat_thread.start()
        self.send_thread.start()
        self.ingest_thread.start()


    def send_to_flight_software(self, json):
        self.enqueue(
            Packet(logs=[Log(
                header=json['header'],
                message=json['message'],
                timestamp=time.time())
            ])
        )


    def send(self):
        """ Constantly sends next packet from queue to flight software """
        while self.running:
            try:
                if self.queue_send and SEND_ALLOWED:
                    packet_str = heapq.heappop(self.queue_send)[1]

                    subpackets = [packet_str[i:255+i] for i in range(0, len(packet_str), 255)] #split into smaller packets of 255
                    print(subpackets)

                    for subpacket in subpackets:
                        self.ser.write(subpacket)
                        print("\nSent packet:", subpacket, "\n")

                time.sleep(DELAY_SEND)
            except Exception as e:
                print("ERROR:", e)
                self.running = False


    def listen(self):
        """ Constantly listens for any from ground station """
        while self.running:
            rcvd = ser.read(ser.in_waiting).decode()
            self.rcvd_data.append(rcvd)
            if '$' in data:
                i = data.find("$")      # end of packet char
                packet = data[:i]
                self.ingest_queue.put(packet)

                data = data[i+1:]
                    
            time.sleep(0.01)


    def enqueue(self, packet):
        """ Encrypts and enqueues the given Packet """
        # TODO: This is implemented wrong. It should enqueue by finding packets that have similar priorities, not changing the priorities of current packets.
        packet_str = (packet.to_string() + "$").encode()
        heapq.heappush(self.queue_send, (packet.priority, packet_str))

    
    def ingest_loop(self):
        """ Constantly ingests queue data, blocking until an item is available from the queue """
        while self.running:
            # block=True waits until an item is available
            # We add a timeout so the loop can stop
            try:
                data = self.ingest_queue.get(block=True, timeout=1)
                self.ingest(data)
            except Empty:
                pass


    def ingest(self, packet_str):
        """ Prints any packets received """
        packet_str = packet_str
        packet_strs = packet_str.split("END")[:-1]
        packets = [Packet.from_string(p_str) for p_str in packet_strs]
        for packet in packets:
            for log in packet.logs:
                log.timestamp = round(log.timestamp, 1)   #########CHANGE THIS TO BE TIMESTAMP - START TIME IF PYTHON

                if "heartbeat" in log.header or "stage" in log.header or "response" in log.header or "mode" in log.header:
                    self.update_general(log.__dict__)

                if "sensor_data" in log.header:
                    self.update_sensor_data(log.__dict__)

                if "valve_data" in log.header:
                    self.update_valve_data(log.__dict__)
                
                log.save()

    def heartbeat(self):
        """ Constantly sends heartbeat message """
        while self.running:
            log = Log(header="heartbeat", message="AT")
            self.enqueue(Packet(logs=[log], priority=LogPriority.INFO))
            print("Sent heartbeat")
            time.sleep(DELAY_HEARTBEAT)

    ## backend methods

    def update_general(self, log):
        log_send('general', log)
        self.socketio.emit('general', log, broadcast=True)
    
    
    def update_sensor_data(self, log):
        log_send('sensor', log)
        self.socketio.emit('sensor_data', log, broadcast=True)

    
    def update_valve_data(self, log):
        log_send('valve', log)
        self.socketio.emit('valve_data', log, broadcast=True)

    def update_store_data(self):
        self.socketio.emit('general_copy', self.general_copy)
        self.socketio.emit('sensors_copy', self.sensors_copy)
        self.socketio.emit('valves_copy', self.valves_copy)
        self.socketio.emit('buttons_copy', self.buttons_copy)

    ## store copy methods
    def update_general_copy(self, general):
        self.general_copy = general

    def update_sensors_copy(self, sensors):
        self.sensors_copy = sensors

    def update_valves_copy(self, valves):
        self.valves_copy = valves

    def update_buttons_copy(self, buttons):
        self.buttons_copy = buttons

    def on_button_press(self, data):
        log_send('button', data)
        if data['header'] == 'update_general':
            self.update_general_copy(data['message'])
        elif data['header'] == 'update_sensors':
            self.update_sensors_copy(data['message'])
        elif data['header'] == 'update_valves':
            self.update_valves_copy(data['message'])
        elif data['header'] == 'update_buttons':
            self.update_buttons_copy(data['message'])
        elif data['header'] == 'store_data':
            self.update_store_data()
        else:
            print(data)
            log = Log(header=data['header'], message=data['message'])
            self.enqueue(Packet(logs=[log], priority=LogPriority.INFO))

hidden_log_types = set() # {"general", "sensor", "valve", "button"}
def log_send(type, log):
    if type not in hidden_log_types:
        print(f"Sending [{type}] {log}")