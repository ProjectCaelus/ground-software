import json
from handler import Handler

from flask import Flask, render_template
from flask_cors import CORS
from flask_socketio import SocketIO, emit, Namespace
import time
import logging

import argparse

# XBEE - ADD TO CONFIG
GS_PORT = "COM7"
BAUD_RATE = 9600
FLIGHT_NODE_ID = "Flight"


log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

config = {}

parser = argparse.ArgumentParser(description='Run the Project Caelus Ground Station Server.', formatter_class=argparse.RawTextHelpFormatter)

parser.add_argument('--config', help="The config file to use for the simulation (enter " + 
        "local if you want to run the simulation on the default local config). \n" + 
        "Default: config.json")

args = parser.parse_args()

if args.config == "local":
    config = json.loads(open("config.json").read())
    config["telemetry"]["GS_IP"] = "127.0.0.1"
    config["telemetry"]["SOCKETIO_HOST"] = "127.0.0.1"
elif args.config != None:
    try:
        config = json.loads(open(args.config).read())
    except:
        raise Exception("Error reading from config file '" + args.config + "'")
else:
    config = json.loads(open("config.json").read())



# GS_IP = config["telemetry"]["GS_IP"]
# GS_PORT = config["telemetry"]["GS_PORT"]

app = Flask(__name__, static_folder="templates")
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

time.sleep(1)

if __name__ == "__main__":
    print("listening and sending")

    h = Handler('/')
    h.init(GS_PORT, BAUD_RATE, FLIGHT_NODE_ID)
    h.begin()

    socketio.on_namespace(h)
    socketio.run(app, host=config["telemetry"]["SOCKETIO_HOST"], port=int(config["telemetry"]["SOCKETIO_PORT"]))


    # while True:
    #     temp = input("")
    #     header = temp[:temp.index(" ")]
    #     message = temp[temp.index(" ") + 1:]
    #     pack = Packet(header=header)
    #     log = Log(header=header, message=message)
    #     pack.add(log)
    #     enqueue(Packet(header="MESSAGE", logs=[log]))