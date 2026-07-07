import socket
import time
import json
import copy
import os
import sys
import psutil
import threading

from gps import GPS
from msp import MSP
from camera import Camera
from timer import Timer


class DroneController:

    # multiwii command constants (https://www.hamishmb.com/multiwii/wiki/index.php?title=Multiwii_Serial_Protocol)
    MSP_STATUS = 101
    MSP_RAW_IMU = 102
    MSP_ATTITUDE = 108
    MSP_ALTITUDE = 109
    MSP_SET_RAW_RC = 200
    MSP_ACC_CALIBRATION = 205
    MSP_MAG_CALIBRATION = 206

    # connection settings
    # DRONE_IP_ADDRESS = "192.168.178.52"  # with fritz.box 7490
    DRONE_IP_ADDRESS = "192.168.4.1"  # with raspi Hotspot
    UPLINK_PORT = 1100
    UPLINK_RECEIVE_BUFFER_SIZE = 1024  # bytes
    DOWNLINK_PORT = 1101

    # timing
    UPLINK_TIMEOUT = 0.005  # secs (results in mainloop cycles of about 200/sec)
    REPEAT_MODE_TIME = 0.06  # secs (repeat previous motor control cmd after this time)
    FAILSAFE_MODE_TIME = 0.3  # secs (go into failsafe when no motor control data available)
    DATA_LOOP_CYCLE_TIMES = 10  # times per sec

    FAILSAFE_CMD = [1500, 1500, 1500, 1500, 1500, 1000, 1000, 2500]  # roll, pitch, yaw, throttle, aux1, aux2, aux3, aux4

    def __init__(self):
        print(f"[INIT] program started")

        # uplink socket connection (drone is server)
        self.up_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.up_sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.UPLINK_RECEIVE_BUFFER_SIZE)
        self.up_sock.settimeout(self.UPLINK_TIMEOUT)
        self.up_sock.bind(("", self.UPLINK_PORT))  # all interfaces -> works on the hotspot and any shared WiFi
        print("[INIT] uplink socket created (server)")

        # downlink socket connection (drone is client)
        self.down_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print("[INIT] downlink socket created (client)")

        # multiwii serial port (USB)
        self.multiwii = MSP()
        print("[INIT] multiwii started")

        # gps serial
        self.gps = GPS()
        print("[INIT] gps created")

        # camera (stream and recording)
        self.camera = Camera()
        print("[INIT] camera created")

        self.last_control_id = 0
        self.last_status_time = time.perf_counter()
        self.last_control_time = time.perf_counter()
        self.last_cycle_time = time.perf_counter()
        self.control_loop_cycle_time = 0  # loops per second, average with exponential decay
        self.control_cycle_time = 0
        self.last_error_reset_time = time.perf_counter()
        self.control_error_counter = 0
        self.last_received_address = None  # ip address, port
        self.last_motor_cmd = [1500, 1500, 1500, 1000, 1000, 1000, 1000, 1000]  # roll, pitch, yaw, throttle, aux1, aux2, aux3, aux4

        self.data_loop_thread = threading.Thread(target=self.data_loop)
        self.data_loop_queue = []
        self.data_loop_timer = Timer(frequency=self.DATA_LOOP_CYCLE_TIMES)

        self.running = False

    def start(self):
        self.gps.start()
        self.running = True
        self.data_loop_thread.start()
        self.control_loop()

    def stop(self):
        self.running = False
        self.data_loop_thread.join()
        self.gps.kill()
        self.camera.stop()
        self.up_sock.close()
        self.down_sock.close()

    def data_loop(self):
        while self.running:
            try:
                # process commands that requested data
                while len(self.data_loop_queue) > 0:
                    command, data = self.data_loop_queue.pop()

                    if command == "GET_BAROMETER_AND_GPS":
                        msp_command, data = self.multiwii.query(self.MSP_ALTITUDE)
                        if msp_command == self.MSP_ALTITUDE:
                            latitude, longitude, num_sats = self.gps.get()
                            self.down_sock.sendto(json.dumps(["GET_BAROMETER_AND_GPS", [data["est_alt"], latitude, longitude, num_sats]]).encode(),
                                                  (self.last_received_address[0], self.DOWNLINK_PORT))

                    elif command == "GET_ATTITUDE":
                        msp_command, data = self.multiwii.query(self.MSP_ATTITUDE)
                        if msp_command == self.MSP_ATTITUDE:
                            self.down_sock.sendto(json.dumps(["GET_ATTITUDE", [data["ang_x"], data["ang_y"], data["heading"]]]).encode(),
                                                  (self.last_received_address[0], self.DOWNLINK_PORT))

                    elif command == "GET_SYSTEM_STATUS":
                        # read CPU and RAM load
                        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                            cpu_temp = float(f.readline())/1000
                        ram_load = psutil.virtual_memory().percent

                        # read multiwii status
                        msp_command, data = self.multiwii.query(self.MSP_STATUS)
                        if msp_command == self.MSP_STATUS:
                            multiwii_cycle_time = data["cycle_time"]
                        else:
                            multiwii_cycle_time = None

                        self.down_sock.sendto(json.dumps(["GET_SYSTEM_STATUS", [cpu_temp, ram_load,
                                                                                  round(1 / self.control_loop_cycle_time) if self.control_loop_cycle_time > 0 else 0,
                                                                                  round(1 / self.control_cycle_time) if self.control_cycle_time > 0 else 0,
                                                                                  round(self.data_loop_timer.get_average_frequency()),
                                                                                  self.control_error_counter,
                                                                                  multiwii_cycle_time,
                                                                                  self.camera.libcamera_stream_running(),
                                                                                  self.camera.libcamera_record_running(),
                                                                                  self.gps.is_alive()]]).encode(),
                                              (self.last_received_address[0], self.DOWNLINK_PORT))

                    # calibrate magnetometer
                    elif command == "CALIBRATE_MAGNETOMETER":
                        _, _ = self.multiwii.query(self.MSP_MAG_CALIBRATION)

                    # calibrate accelerometer
                    elif command == "CALIBRATE_ACCELEROMETER":
                        _, _ = self.multiwii.query(self.MSP_ACC_CALIBRATION)

                    elif command == "START_ARUCO_SYSTEM":
                        pass

                    elif command == "STOP_ARUCO_SYSTEM":
                        pass

                    elif command == "GET_ARUCO_POSITION":
                        pass

                    elif command == "START_VIDEO_STREAM":
                        ip, port, quality = data[0], data[1], data[2]
                        self.camera.start_video_stream(ip, port, quality)

                    elif command == "STOP_VIDEO_STREAM":
                        self.camera.stop_video_stream()

                    elif command == "START_VIDEO_RECORD":
                        self.camera.start_video_record()

                    elif command == "STOP_VIDEO_RECORD":
                        self.camera.stop_video_record()

                    elif command == "TAKE_PHOTO":
                        self.camera.take_photo()

                    elif command == "DELETE_VIDEO_RECORDS":
                        self.camera.delete_video_records()

                    elif command == "STOP_PROGRAM":
                        self.stop()

                    elif command == "REBOOT":
                        os.system("sudo reboot -h now")

                self.data_loop_timer.wait()

            except Exception as err:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                print("[COLLECT_DATA] error in collect-loop:", err, exc_type, "line:", exc_tb.tb_lineno)

    def control_loop(self):
        while self.running:
            try:
                # uplink receive packets
                try:
                    raw_udp_data, self.last_received_address = self.up_sock.recvfrom(256)
                    command, data = json.loads(raw_udp_data.decode())  # every message is ["COMMAND", [data...]]
                except Exception:  # unparsable or foreign packet -> drop
                    command, data = None, None

                if command == "SET_RC_DATA":
                    if data[0] > self.last_control_id:  # check control packet id
                        self.multiwii.send(self.MSP_SET_RAW_RC, data[1:9])
                        self.last_motor_cmd = copy.copy(data[1:9])

                        self.control_cycle_time = (time.perf_counter() - self.last_control_time) * 0.05 + self.control_cycle_time * 0.95
                        self.last_control_time = time.perf_counter()

                elif command == "SET_ARUCO_POSITION":
                    pass

                elif command == "GET_PING":
                    self.down_sock.sendto(json.dumps(["GET_PING", data]).encode(), (self.last_received_address[0], self.DOWNLINK_PORT))

                else:  # data requests get processed in the data loop
                    self.data_loop_queue.append((command, data))

                # failsafe mode
                if time.perf_counter() - self.last_control_time > self.FAILSAFE_MODE_TIME:
                    self.last_control_id = 0  # reset control_id counter after failsafe time (if counter on controller side gets reset)
                    self.control_error_counter += 1

                    # check if armed (aux1 > 1250), then activate failsafe
                    if self.last_motor_cmd[4] > 1250:
                        self.multiwii.send(self.MSP_SET_RAW_RC, self.FAILSAFE_CMD)
                        print(f"[FAILSAFE MODE]: {self.FAILSAFE_CMD}")

                # repeat mode (repeat last motor command if last command is too old)
                elif time.perf_counter() - self.last_control_time > self.REPEAT_MODE_TIME:
                    self.multiwii.send(self.MSP_SET_RAW_RC, self.last_motor_cmd)
                    self.control_error_counter += 1

                # calculate mainloop runtime
                self.control_loop_cycle_time = (time.perf_counter() - self.last_cycle_time) * 0.01 + self.control_loop_cycle_time * 0.99
                self.last_cycle_time = time.perf_counter()

                # reset error counters
                if time.perf_counter() - self.last_error_reset_time > 1:
                    self.last_error_reset_time = time.perf_counter()
                    self.control_error_counter = 0

            except Exception as err:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                print("\nError in loop:", err, exc_type, "line:", exc_tb.tb_lineno)


if __name__ == "__main__":
    drone_controller = DroneController()
    drone_controller.start()
