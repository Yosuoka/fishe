"""program to manage the fishe"""

import time

import rudder
import propeller
import arduino_communicator


def main():
    com = arduino_communicator.ArduinoCommunicator()
    time.sleep(5)
    rud = rudder.Rudder(com)
    prop = propeller.Propeller(com)

    rud.start()
    prop.start()

    try:
        while True:
            rud.set_angle(int(input("angle: ")))
            prop.set_speed(int(input("speed: ")))
    except KeyboardInterrupt:
        rud.stop()
        prop.stop()
