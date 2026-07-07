import customtkinter
import sys
import time
import os
import threading
import subprocess
import socket
import json
import appscript

from joystick_handler_hidapi import JoystickHandler
from ui_frames.live_plot_frame import LivePlotFrame
from ui_frames.status_frame import StatusFrame
from ui_frames.control_frame import ControlFrame
from ui_frames.map_frame import MapFrame
from timer import Timer


def get_local_ip(target_ip: str) -> str:
    """Return this machine's LAN IP on the interface that routes to target_ip.

    Replaces socket.gethostbyname(socket.gethostname()), which returns
    127.0.0.1 on macOS when the ".local" hostname isn't in /etc/hosts. The
    UDP connect() sends no packets; it just makes the OS pick the source
    address for that route.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect((target_ip, 1))
        return s.getsockname()[0]
    finally:
        s.close()


class ControllerApp(customtkinter.CTk):

    UPLINK_PORT = 1100
    DOWNLINK_PORT = 1101
    VIDEO_STREAM_PORT = 1235

    DRONE_HOSTNAME = "raspi-cm4.local"  # resolved via mDNS, works on any shared WiFi
    DRONE_FALLBACK_IP = "192.168.4.1"  # with RaspberryPi access point (hostname not resolvable -> assume hotspot)
    DOWN_ADDRESS = ("", DOWNLINK_PORT)  # bind downlink on all interfaces; the drone's IP for the video stream is resolved live in start_video_stream()

    RASPBERRY_PI_USERNAME = "pi"
    DRONE_VIDEO_RECORDS_PATH = "/home/pi/drone/video_records"
    COMPUTER_VIDEO_RECORDS_PATH = os.path.dirname(os.path.abspath(__file__))

    STATUS_DATA_INTERVAL = 1  # secs

    def __init__(self):
        customtkinter.set_appearance_mode("dark")  # plot + panel colors are tuned for the dark theme
        super().__init__()
        self.title("Controller App")
        self.geometry("1570x700")

        # resolve the drone's address: mDNS hostname when on a shared WiFi, fixed IP on the drone's own hotspot
        try:
            drone_ip = socket.gethostbyname(self.DRONE_HOSTNAME)
            print(f"drone found via mDNS: {self.DRONE_HOSTNAME} -> {drone_ip}")
        except socket.gaierror:
            drone_ip = self.DRONE_FALLBACK_IP
            print(f"{self.DRONE_HOSTNAME} not resolvable, assuming drone hotspot: {drone_ip}")
        self.UP_ADDRESS = (drone_ip, self.UPLINK_PORT)

        # map database
        self.map_database = os.path.dirname(os.path.abspath(__file__)) + "/offline_map_tiles.db"

        self.joystick_handler = JoystickHandler()

        self.last_update_drone_data_time = time.time()

        # WiFi link SNR monitoring via CoreWLAN (replaces the removed `airport` CLI tool).
        # Disabled gracefully if the framework isn't installed so it never spams the console.
        self.wifi_interface = None
        try:
            import CoreWLAN
            self.wifi_interface = CoreWLAN.CWWiFiClient.sharedWiFiClient().interface()
        except Exception:
            print("WiFi SNR monitoring disabled — run `pip install pyobjc-framework-CoreWLAN` to enable it.")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.live_plot_frame = LivePlotFrame(self)
        self.live_plot_frame.grid(row=0, column=0, rowspan=2, sticky="ns")

        self.status_frame = StatusFrame(self)
        self.status_frame.grid(row=1, column=2, sticky="nsew")

        self.map_frame = MapFrame(self, app_reference=self)
        self.map_frame.grid(row=0, column=2, sticky="nsew")

        self.control_frame = ControlFrame(self, app_reference=self, fg_color="transparent")
        self.control_frame.grid(row=0, column=1, rowspan=2, sticky="nsew")

        self.mpv_process = None

        # uplink
        self.up_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # create UDP socket for uplink
        self.up_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024)
        self.up_socket.settimeout(0.01)
        self.uplink_thread = threading.Thread(target=self.uplink, daemon=True)  # create uplink thread
        self.uplink_timer = Timer(frequency=120)  # create timer for uplink
        self.uplink_rc_message_counter = 1

        # downlink
        self.down_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # create UDP socket for downlink
        self.down_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4096)
        self.down_socket.bind(self.DOWN_ADDRESS)
        self.down_socket.settimeout(0.1)
        self.downlink_thread = threading.Thread(target=self.downlink, daemon=True)  # create downlink thread

    def open_video_stream(self):
        """ open mpv listening on the UDP video port; the drone pushes raw h264 directly to it.
            window opens immediately and shows the stream as soon as data arrives """
        if self.mpv_process is None or self.mpv_process.poll() is not None:
            self.mpv_process = subprocess.Popen(["mpv", "--force-window=immediate", "--no-terminal",
                                                 "--profile=low-latency", "--untimed", "--framedrop=decoder",
                                                 "--cache=no", "--demuxer-lavf-format=h264",
                                                 "--title=video-stream",
                                                 f"udp://0.0.0.0:{self.VIDEO_STREAM_PORT}?fifo_size=100000&overrun_nonfatal=1"],
                                                shell=False)

    def send_command(self, command: str, data: list = None):
        """ every message to the drone is a JSON array ["COMMAND", [data...]] in a single UDP datagram """
        message = json.dumps([command, data if data is not None else []])
        self.up_socket.sendto(message.encode(), self.UP_ADDRESS)

    def calibrate_magnetometer(self):
        self.send_command("CALIBRATE_MAGNETOMETER")

    def calibrate_accelerometer(self):
        self.send_command("CALIBRATE_ACCELEROMETER")

    def start_video_stream(self):
        quality = self.control_frame.video_stream_quality_menu.get()
        local_ip = get_local_ip(self.UP_ADDRESS[0])  # this machine's IP on the network reaching the drone
        self.send_command("START_VIDEO_STREAM", [local_ip, self.VIDEO_STREAM_PORT, quality])

    def stop_video_stream(self):
        self.send_command("STOP_VIDEO_STREAM")

    def start_video_record(self):
        self.send_command("START_VIDEO_RECORD")

    def stop_video_record(self):
        self.send_command("STOP_VIDEO_RECORD")

    def take_photo(self):
        self.send_command("TAKE_PHOTO")

    def delete_video_records(self):
        self.send_command("DELETE_VIDEO_RECORDS")

    def download_video_record(self):
        appscript.app('Terminal').do_script(f"scp -r {self.RASPBERRY_PI_USERNAME}@{self.UP_ADDRESS[0]}:{self.DRONE_VIDEO_RECORDS_PATH} " +
                                            f"{self.COMPUTER_VIDEO_RECORDS_PATH}")

    def stop_program(self):
        self.send_command("STOP_PROGRAM")

    def reboot(self):
        self.send_command("REBOOT")

    def downlink(self):
        last_signal_strength_time = time.time()

        while True:
            try:
                try:
                    raw_down_data, address = self.down_socket.recvfrom(1024)
                    command, data = json.loads(raw_down_data.decode())
                except Exception:  # unparsable or foreign packet -> drop
                    command, data = None, None

                if command == "GET_PING":
                    ping_time = time.time() - data[0]
                    self.live_plot_frame.ping_plot_queue.append(ping_time)

                elif command == "GET_BAROMETER_AND_GPS":
                    self.live_plot_frame.height_plot_queue.append(data[0])
                    self.status_frame.set_gps_satellites(data[3])
                    self.status_frame.set_position(data[1], data[2])
                    self.map_frame.set_target_position(data[1], data[2])

                elif command == "GET_ATTITUDE":
                    pass

                elif command == "GET_ARUCO_POSITION":
                    pass

                elif command == "GET_SYSTEM_STATUS":
                    self.status_frame.set_cpu_temp(data[0])
                    self.status_frame.set_ram_load(data[1])
                    self.status_frame.set_control_loop_cycles(data[2])
                    self.status_frame.set_control_cycles(data[3])
                    self.status_frame.set_data_loop_cycles(data[4])
                    self.live_plot_frame.control_error_plot_queue.append(data[5])
                    self.status_frame.set_multiwii_cycles(data[6])
                    self.status_frame.set_video_stream_status(data[7])
                    self.status_frame.set_video_record_status(data[8])
                    self.status_frame.set_gps_status(data[9])

                # read wifi signal above noise value (SNR of the link to the drone AP)
                if self.wifi_interface is not None and time.time() - last_signal_strength_time > 0.5:
                    last_signal_strength_time = time.time()
                    snr_value = self.read_wifi_snr()
                    if snr_value is not None:
                        self.live_plot_frame.snr_plot_queue.append(snr_value)

            except Exception as error:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                print("Error in downlink:", error, exc_type, "line:", exc_tb.tb_lineno)

    def read_wifi_snr(self):
        """ signal-to-noise ratio (dB) of the WiFi link to the drone AP, or None if unavailable """
        if self.wifi_interface is None:
            return None
        try:
            return float(self.wifi_interface.rssiValue()) - float(self.wifi_interface.noiseMeasurement())
        except Exception:
            return None

    def uplink(self):
        self.joystick_handler.init_joystick()
        self.calibrate_accelerometer()
        self.calibrate_magnetometer()

        while True:
            try:
                # send joystick control data
                try:
                    joystick_values, success = self.joystick_handler.get()
                    self.send_command("SET_RC_DATA", [self.uplink_rc_message_counter] + joystick_values)
                    self.uplink_rc_message_counter += 1
                    self.control_frame.set_joystick_values(joystick_values)
                except socket.error as err:
                    print("uplink socket error:", err)

                # send data requests
                if time.time() - self.last_update_drone_data_time > self.STATUS_DATA_INTERVAL:
                    self.last_update_drone_data_time = time.time()
                    try:
                        self.send_command("GET_PING", [time.time()])
                        self.send_command("GET_BAROMETER_AND_GPS")
                        self.send_command("GET_ATTITUDE")
                        self.send_command("GET_SYSTEM_STATUS")
                        self.send_command("GET_ARUCO_POSITION")
                    except socket.error as err:
                        print("uplink socket error:", err)

                self.uplink_timer.wait()

            except Exception as err:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                print("uplink exception:", err, exc_type, "line:", exc_tb.tb_lineno)

    def bring_to_front(self):
        """ pull the window in front of other apps and give it focus on startup (macOS) """
        self.lift()
        self.attributes("-topmost", True)
        self.after_idle(self.attributes, "-topmost", False)  # raise above all, then stop pinning it on top
        self.focus_force()
        try:
            # make the terminal-launched Python process the active app so the window actually comes forward
            from AppKit import NSApplication
            NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        except Exception:
            pass

    def start(self):
        self.downlink_thread.start()
        self.uplink_thread.start()
        self.after(100, self.bring_to_front)  # run once the mainloop is up and the window is drawn
        self.mainloop()


if __name__ == "__main__":
    app = ControllerApp()
    app.start()
