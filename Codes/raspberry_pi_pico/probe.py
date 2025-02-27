"""main class of the probe, with attributes for each sensor"""
from thermometer import Thermometer
from pHMeter import PHMeter
from tdsSensor import TDSSensor
import secret_data
import uos
import network
import urequests
import random
import ujson
import machine
import utime

def to_standart_time(gmtime):
    return f"{gmtime[0]}-{gmtime[1]}-{gmtime[2]} {gmtime[3]}:{gmtime[4]}:{gmtime[5]}"


class Probe:
    "probe class"

    def __init__(
        self,
        pH_meter: PHMeter,
        thermometer: Thermometer,
        tds_sensor: TDSSensor,
        probe_id: int = 0,
    ):
        self.led=machine.Pin("LED")
        self.pHMeter = pH_meter
        self.thermometer = thermometer
        self.tdsSensor = tds_sensor
        listdir = uos.listdir()
        self.measureId = 0
        self.data_file = "data_to_send.csv"
        self.probeId = probe_id
        if self.data_file not in listdir:
            self.generate_data_file()
        self.connect_wifi()

    def connect_wifi(self):
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        wlan.connect(secret_data.wifi_id, secret_data.pswd)

        # Wait for connect or fail
        wait = 10
        while wait > 0:
            if wlan.status() < 0 or wlan.status() >= 3:
                break
            wait -= 1
            print("waiting for connection...")
            for i in range(11):
                utime.sleep(0.1)
                self.led.toggle()
        # Handle connection error
        if wlan.status() != 3:
            raise RuntimeError("wifi connection failed")
        print("connected")
        ip = wlan.ifconfig()[0]
        print("IP: ", ip)

    def generate_data_file(self):
        with open("data_to_send.csv", "w") as f:
            f.write(
                "MeasureId,ProbeID,Temperature,PH,Turbidity,Zposition,XPosition,YPosition,Date\n"
            )

    def measure(self):
        try:
            temperature = self.thermometer.measure()
        except Exception as e:
            print("thermometer failed: ", e)
            temperature = -1
        try:
            ph = self.pHMeter.measure()
        except Exception as e:
            print("pH meter failed: ", e)
            ph = -1
        try:
            self.tdsSensor.set_temp(temperature)
            turbidity = self.tdsSensor.measure()
        except Exception as e:
            print("TDS sensor failed: ", e)
            turbidity = -1
        with open(self.data_file, "a") as data:
            data.write(
                f"""{self.measureId},{self.probeId},{temperature},{ph},{turbidity},{0},{0},{0},{to_standart_time(utime.gmtime())}\n"""
            )
        print(f"""pH : {ph}
Temperature : {temperature}
Turbidity : {turbidity}
""")
        for i in range(2):
            self.led.on()
            utime.sleep(0.5)
            self.led.off()
            utime.sleep(0.5)


    def test(self):
        try:
            self.pHMeter.test()
        except Exception as e:              # should be more specific, like Assertion error, but I'm beeing careful
            print("pH meter failed: ", e)
        try:
            self.thermometer.test()
        except Exception as e:
            print("thermometer failed: ", e)
        try:
            self.tdsSensor.test()
        except Exception as e:
            print("TDS sensor failed: ", e)

    def send_data(self):
        try:
            self.connect_wifi()
        except RuntimeError:
            print("wifi connection failed, keeping data for later")
            return
        with open(self.data_file) as data_raw:
            data = data_raw.readlines()
            if (
                data[0].strip()
                != "MeasureId,ProbeID,Temperature,PH,Turbidity,Zposition,XPosition,YPosition,Date"
            ):
                self.generate_data_file()
        try:
            r2 = urequests.get("http://192.168.34.199/api/measure/?format=api")
            print(str(r2.__dict__))
            print(r2.content.decode())

        except Exception as e:
            print(e)
        buffer_failed = ["MeasureId,ProbeID,Temperature,PH,Turbidity,Zposition,XPosition,YPosition,Date"]
        for d in data[1:]:
            d_list = d.split(",")
            r3 = urequests.post(
                "http://192.168.34.199/api/measure/",
                headers={"content-type": "application/json"},
                data=ujson.dump(
                    "data",
                    {
                        "temperature": d_list[2],
                        "pH": d_list[3],
                        "turbidity": d_list[4],
                        "x_position": d_list[6],
                        "y_position": d_list[7],
                        "z_position": d_list[5],
                        "probe": 1,
                        "time": d_list[8],
                    },
                ),
            )
            if r3.status_code == 200:
                print("sent!")
                for i in range(10):
                    for _ in range(10):
                        self.led.on()
                        utime.sleep(0.01*(i/10))
                        self.led.off()
                        utime.sleep(0.01*((-i+10)/10))
            else:
                print(f"failed:{r3.status_code}")
                print(d)
                buffer_failed.append(d)
                for i in range(10):
                    for _ in range(10):
                        self.led.on()
                        utime.sleep(0.01*((-i+10)/10))
                        self.led.off()
                        utime.sleep(0.01*(i/10))

        with open(self.data_file, "w") as data_raw:
            data_raw.write("\n".join(buffer_failed))


if __name__ == "__main__":
    probe = Probe(PHMeter(), Thermometer(), TDSSensor())
    probe.test()
    while True:
        probe.measure()
        probe.send_data()
