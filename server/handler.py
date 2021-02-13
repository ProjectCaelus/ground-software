import time
import heapq
import threading
from packet import Packet, Log, LogPriority
from flask_socketio import SocketIO, emit, Namespace
from digi.xbee.devices import XBeeDevice

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
    """ Telemetry Class handles all communication """

    def init(self, port, baud_rate, remote_id):
        """ Based on given IP and port, create and connect a socket """
        self.queue_send = []
        self.device = XBeeDevice(port, baud_rate)
        self.start_time = time.time()
        self.connect(remote_id)


    ## telemetry methods
    def connect(self, remote_id):
        try:
            self.device.open()

            self.remote_device = device.get_network().discover_device(remote_id)
            if remote_device is None:
                print("Could not find the remote device")
                
            self.device.add_data_received_callback(self.ingest)
        except:
            print("Error opening XBee device")


    def begin(self):
        """ Starts the send and listen threads """
        self.send_thread = threading.Thread(target=self.send)
        self.send_thread.daemon = True
        self.listen_thread = threading.Thread(target=self.listen)
        self.listen_thread.daemon = True
        self.heartbeat_thread = threading.Thread(target=self.heartbeat)
        self.heartbeat_thread.daemon = True
        self.send_thread.start()
        self.listen_thread.start()
        self.heartbeat_thread.start()


    def send(self):
        """ Constantly sends next packet from queue to flight """
        while True:
            if self.queue_send and SEND_ALLOWED:
                encoded = heapq.heappop(self.queue_send)[1]
                self.device.send_data(self.remote_device, encoded)
                print("\nSent packet: \n", encoded.decode(), "\n")

            time.sleep(DELAY_SEND)


    def enqueue(self, packet):
        """ Encrypts and enqueues the given Packet """
        # TODO: This is implemented wrong. It should enqueue by finding packets that have similar priorities, not changing the priorities of current packets.
        packet.timestamp = time.time()
        print("\nEnqueuing packet: \n", packet.to_string(), "\n")
        packet_str = (packet.to_string() + "END").encode()
        heapq.heappush(self.queue_send, (packet.priority, packet_str))


    def ingest(self, xbee_message):
        """ Prints any packets received """
#        print("Ingesting:", packet_str)
        packet_str = xbee_message.data.decode()
        packet_str = packet_str.decode()
        packet_strs = packet_str.split("END")[:-1]
        packets = [Packet.from_string(p_str) for p_str in packet_strs]
        #packet = Packet.from_string(packet_str)
        for packet in packets:
            for log in packet.logs:
                log.timestamp = round(log.timestamp, 1)   #########CHANGE THIS TO BE TIMESTAMP - START TIME IF PYTHON
#                print("Timestamp:", log.timestamp)
                if "heartbeat" in log.header or "stage" in log.header or "response" in log.header or "mode" in log.header:
                    self.update_general(log.__dict__)

                if "sensor_data" in log.header:
                    self.update_sensor_data(log.__dict__)

                if "valve_data" in log.header:
                    self.update_valve_data(log.__dict__)
                
                log.save()

    def heartbeat(self):
        """ Constantly sends heartbeat message """
        while True:
            log = Log(header="heartbeat", message="AT")
            log.timestamp = time.time()

            self.enqueue(Packet(logs=[log], priority=LogPriority.INFO))
            print("Sent heartbeat")
            time.sleep(DELAY_HEARTBEAT)

    ## backend methods

    def update_general(self, log):
        print("General:", log)
        self.socketio.emit('general',  log)
    
    
    def update_sensor_data(self, log):
        print("Sensor:", log)
        self.socketio.emit('sensor_data',  log)

    
    def update_valve_data(self, log):
        print("Valve:", log)
        self.socketio.emit('valve_data',  log)


    def on_button_press(self, data):
        print(data)
        log = Log(header=data['header'], message=data['message'])
        self.enqueue(Packet(logs=[log], priority=LogPriority.INFO))