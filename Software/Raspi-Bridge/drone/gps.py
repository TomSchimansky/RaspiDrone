import multiprocessing
import serial
import pynmea2
import sys


class GPS(multiprocessing.Process):
    r"""
    Commands that may be necessary for the GPS to work:
    - sudo chmod 666 <GPS_PATH>
    - sudo systemctl stop serial-getty@ttyAMA0.service
    - gpio mode 15 ALT0
    - gpio mode 16 ALT0

    Configure GPS module:
    - stty -F /dev/ttyAMA0 115200 (configure baudrate of serial port)

    - echo -e '\$PMTK251,115200*1F\r\n' > /dev/ttyAMA0 (115200 Baudrate)

    - echo -e '\$PMTK220,1000*1F\r\n' > /dev/ttyAMA0 (1Hz Internal Rate)
    - echo -e '\$PMTK220,500*2B\r\n' > /dev/ttyAMA0 (2Hz Internal Rate)
    - echo -e '\$PMTK220,200*2C\r\n' > /dev/ttyAMA0 (5Hz Internal Rate)

    - echo -e '\$PMTK300,1000,0,0,0,0*1C\r\n' > /dev/ttyAMA0 (1Hz Position Fix)
    - echo -e '\$PMTK300,200,0,0,0,0*2F\r\n' > /dev/ttyAMA0 (5Hz Position Fix)

    - echo -e '\$PMTK314,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0*29\r\n' > /dev/ttyAMA0 (GPGGA Format)

    Usage:
    gps = GPS()
    gps.start() (start process)
    values = gps.get()
    running = gps.is_alive()
    gps.kill()
    """

    GPS_PATH = "/dev/ttyAMA0"  # connected via UART
    GPS_SERIAL_READ_TIMEOUT = 0.3  # secs
    GPS_BAUDRATE = 115200

    def __init__(self):
        super().__init__(daemon=True)

        self.shared_coordinates = multiprocessing.Array("f", (0.0, 0.0))
        self.shared_satellites = multiprocessing.Value("i", 0)

        self.port = serial.Serial(self.GPS_PATH, baudrate=self.GPS_BAUDRATE, timeout=self.GPS_SERIAL_READ_TIMEOUT)

    def get(self):
        """ returns latest latitude, longitude, satellite count """
        return self.shared_coordinates[0], self.shared_coordinates[1], self.shared_satellites.value

    def run(self):
        self.port.flushInput()

        while True:
            try:
                gps_message = self.port.readline()
                if gps_message:
                    gps_message = gps_message.decode("ascii")
                    gps_message = gps_message.replace("\r\n", "")
                    gps_sentence = pynmea2.parse(gps_message)

                    if hasattr(gps_sentence, "latitude") and hasattr(gps_sentence, "longitude"):
                        self.shared_coordinates[0] = gps_sentence.latitude
                        self.shared_coordinates[1] = gps_sentence.longitude
                    if hasattr(gps_sentence, "num_sats"):
                        self.shared_satellites.value = int(gps_sentence.num_sats)
            except serial.SerialTimeoutException:
                pass
            except Exception as err:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                print("gps error:", err, exc_type, "line:", exc_tb.tb_lineno)

