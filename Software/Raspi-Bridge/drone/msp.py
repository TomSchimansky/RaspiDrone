import serial
import time
import threading
from typing import Tuple, Union


class MSP:
    """
    Implementation of the multiwii serial protocol by using pyserial, working for the following commands:
    MSP_STATUS, MSP_RAW_IMU, MSP_ATTITUDE, MSP_ALTITUDE, MSP_SET_RAW_RC, MSP_ACC_CALIBRATION, MSP_MAG_CALIBRATION
    """

    # multiwii command constants (https://www.hamishmb.com/multiwii/wiki/index.php?title=Multiwii_Serial_Protocol)
    MSP_STATUS = 101
    MSP_RAW_IMU = 102
    MSP_ATTITUDE = 108
    MSP_ALTITUDE = 109
    MSP_SET_RAW_RC = 200
    MSP_ACC_CALIBRATION = 205
    MSP_MAG_CALIBRATION = 206

    PATH = "/dev/ttyACM0"  # connected via USB
    SERIAL_READ_TIMEOUT = 0.05  # secs
    RESPONSE_TIMEOUT = 0.2  # secs (give up waiting for a response instead of desyncing forever)

    def __init__(self):
        self.port = serial.Serial(self.PATH,
                                  baudrate=115200,
                                  timeout=self.SERIAL_READ_TIMEOUT,
                                  bytesize=serial.EIGHTBITS,
                                  parity=serial.PARITY_NONE,
                                  stopbits=serial.STOPBITS_ONE,
                                  xonxoff=False,
                                  rtscts=False,
                                  dsrdtr=False)
        self.write_lock = threading.Lock()  # send() is called from the control loop and the data loop
        time.sleep(2)  # wait for board to become operational

    def send(self, command: int, data: list = None):
        """ only works for data requests and MSP_SET_RAW_RC """

        output = bytearray(b'$M<')  # create header

        if data is not None:
            data_length = len(data) * 2
        else:
            data_length = 0

        output.append(data_length)  # append data length
        output.append(command)  # append command

        checksum = data_length ^ command
        if data is not None:
            for b in data:
                b_b = b.to_bytes(2, "little")
                output += b_b  # append data values
                checksum = checksum ^ b_b[0]
                checksum = checksum ^ b_b[1]
        output.append(checksum)  # append checksum

        with self.write_lock:  # prevent interleaved frames from concurrent threads
            self.port.write(output)

    def flush_input(self):
        """ discard stale data before sending a request, so receive() matches the fresh response """
        self.port.reset_input_buffer()

    def query(self, command: int) -> Tuple[Union[None, int], Union[None, dict]]:
        """ request data and wait for the matching response.
            the 32u4 multiwii board only transmits a pending response when new serial input
            arrives, so the request is sent twice: the second frame pushes out the response
            to the first. stray/stale frames are skipped until the command matches. """
        self.flush_input()
        self.send(command)
        self.send(command)
        deadline = time.time() + self.RESPONSE_TIMEOUT
        while time.time() < deadline:
            received_command, data = self.receive()
            if received_command == command:
                return received_command, data
        return None, None

    def receive(self) -> Tuple[Union[None, int], Union[None, dict]]:
        # wait for b'$M>' to appear, but give up after RESPONSE_TIMEOUT
        deadline = time.time() + self.RESPONSE_TIMEOUT
        while True:
            header = self.port.read()
            if header == b'$':  # message begins
                header += self.port.read(2)  # read b'M>'
                if header == b'$M>':
                    break
            if time.time() > deadline:
                return None, None

        data_length = int.from_bytes(self.port.read(), "little")  # read data-length
        command = int.from_bytes(self.port.read(), "little")  # read MSP command
        data = self.port.read(data_length)  # read data
        checksum = int.from_bytes(self.port.read(), "little")  # read checksum

        # calculate checksum
        calculated_checksum = data_length ^ command
        for byte in data:
            calculated_checksum ^= byte

        if calculated_checksum == checksum:
            # create dictionary with data values
            data_dict = {}

            # extract values from data
            if command == self.MSP_STATUS:
                data_dict["cycle_time"] = int.from_bytes(data[0:2], "little", signed=False)  # microseconds
                data_dict["i2c_errors_count"] = int.from_bytes(data[2:4], "little", signed=False)
                data_dict["sensor"] = int.from_bytes(data[4:6], "little", signed=False)
                data_dict["flag"] = int.from_bytes(data[6:10], "little", signed=False)
                data_dict["global_conf"] = int.from_bytes(data[10:11], "little", signed=False)

            elif command == self.MSP_RAW_IMU:
                data_dict["acc_x"] = int.from_bytes(data[0:2], "little", signed=True)  # units depend on sensor
                data_dict["acc_y"] = int.from_bytes(data[2:4], "little", signed=True)
                data_dict["acc_z"] = int.from_bytes(data[4:6], "little", signed=True)
                data_dict["gyr_x"] = int.from_bytes(data[6:8], "little", signed=True)
                data_dict["gyr_y"] = int.from_bytes(data[8:10], "little", signed=True)
                data_dict["gyr_z"] = int.from_bytes(data[10:12], "little", signed=True)
                data_dict["mag_x"] = int.from_bytes(data[12:14], "little", signed=True)
                data_dict["mag_y"] = int.from_bytes(data[14:16], "little", signed=True)
                data_dict["mag_z"] = int.from_bytes(data[16:18], "little", signed=True)

            elif command == self.MSP_ATTITUDE:
                data_dict["ang_x"] = int.from_bytes(data[0:2], "little", signed=True)  # 1/10 degree
                data_dict["ang_y"] = int.from_bytes(data[2:4], "little", signed=True)  # 1/10 degree
                data_dict["heading"] = int.from_bytes(data[4:6], "little", signed=True)  # degree

            elif command == self.MSP_ALTITUDE:
                data_dict["est_alt"] = int.from_bytes(data[0:4], "little", signed=True)  # cm
                data_dict["vario"] = int.from_bytes(data[4:6], "little", signed=True)  # cm/s

            return command, data_dict
        else:
            return None, None
