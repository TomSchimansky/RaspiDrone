import subprocess
import sys
import os
from datetime import datetime


class Camera:

    VIDEO_RECORDS_PATH = "/home/pi/drone/video_records"

    # streaming quality presets (bitrate in bit/s, intra = I-frame interval in frames)
    STREAM_QUALITY_PRESETS = {
        "low":    {"width": 640,  "height": 480,  "bitrate": 350000,  "intra": 5},
        "medium": {"width": 640,  "height": 480,  "bitrate": 500000,  "intra": 3},
        "HD":     {"width": 1280, "height": 720,  "bitrate": 2000000, "intra": 3},
        "FullHD": {"width": 1920, "height": 1080, "bitrate": 5000000, "intra": 3},
    }

    def __init__(self):
        self.libcamera_stream_process = None
        self.libcamera_record_process = None
        self.libcamera_photo_process = None

    def stop(self):
        if self.libcamera_stream_running():
            self.libcamera_stream_process.kill()
            self.libcamera_stream_process.wait()
        if self.libcamera_record_running():
            self._stop_record_gracefully()
        if self.libcamera_photo_running():
            self.libcamera_photo_process.kill()
            self.libcamera_photo_process.wait()

    def libcamera_stream_running(self) -> bool:
        return self.libcamera_stream_process is not None and self.libcamera_stream_process.poll() is None

    def libcamera_record_running(self) -> bool:
        return self.libcamera_record_process is not None and self.libcamera_record_process.poll() is None

    def libcamera_photo_running(self) -> bool:
        return self.libcamera_photo_process is not None and self.libcamera_photo_process.poll() is None

    def camera_in_use(self) -> bool:
        return self.libcamera_stream_running() or self.libcamera_record_running() or self.libcamera_photo_running()

    def start_video_stream(self, ip: str, port: int, quality: str):
        """ stream h264 directly over UDP to the ground station (no netcat needed).
            --inline repeats SPS/PPS headers so the player can join a running stream,
            --flush pushes every frame out immediately for minimal latency """
        if not self.camera_in_use():
            preset = self.STREAM_QUALITY_PRESETS.get(quality, self.STREAM_QUALITY_PRESETS["low"])
            try:
                self.libcamera_stream_process = subprocess.Popen(
                    ["libcamera-vid", "--verbose=0", "--timeout=0", "--codec=h264",
                     "--inline", "--flush", "--vflip", "--hflip",
                     f"--width={preset['width']}", f"--height={preset['height']}",
                     "--framerate=25", f"--bitrate={preset['bitrate']}", f"--intra={preset['intra']}",
                     "-o", f"udp://{ip}:{port}"], shell=False)
                print(f"[VIDEO_STREAM] video stream started (udp://{ip}:{port}, {quality})")
            except Exception as err:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                print("[VIDEO STREAM]", err, exc_type, "line:", exc_tb.tb_lineno)

    def stop_video_stream(self):
        if self.libcamera_stream_running():
            self.libcamera_stream_process.kill()
            self.libcamera_stream_process.wait()  # reap, so *_running() reports False immediately
        print("[VIDEO STREAM] video stream stopped")

    def start_video_record(self):
        """ --keypress + stdin pipe allow a graceful stop (flushes the file, no truncated last frame) """
        if not self.camera_in_use():
            try:
                datetime_object = datetime.now()
                self.libcamera_record_process = subprocess.Popen(["libcamera-vid", "--verbose=0", "--timeout=1000000000", "--codec=h264",
                                                                  "--keypress", "--vflip", "--hflip", "--width=1920", "--height=1080", "--framerate=30",
                                                                  "-o", f"{self.VIDEO_RECORDS_PATH}/{datetime_object.strftime('%m-%d-%Y_%H-%M-%S')}.h264"],
                                                                 shell=False, stdin=subprocess.PIPE)
                print("[VIDEO RECORD]", "video record started")
            except Exception as err:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                print("[VIDEO RECORD]", err, exc_type, "line:", exc_tb.tb_lineno)

    def _stop_record_gracefully(self):
        """ ask libcamera-vid to stop via its --keypress mechanism so it flushes the file;
            fall back to kill if it does not exit in time """
        try:
            self.libcamera_record_process.stdin.write(b"x\n")
            self.libcamera_record_process.stdin.flush()
            self.libcamera_record_process.wait(timeout=3)
        except Exception:
            self.libcamera_record_process.kill()
            self.libcamera_record_process.wait()

    def stop_video_record(self):
        if self.libcamera_record_running():
            self._stop_record_gracefully()
        print("[VIDEO RECORD] video record stopped")

    def take_photo(self):
        if not self.camera_in_use():
            try:
                datetime_object = datetime.now()
                self.libcamera_photo_process = subprocess.Popen(["libcamera-jpeg", "--verbose=0", "--vflip", "--hflip", "--timeout=1", "--nopreview", "--quality=100",
                                                                 "-o", f"{self.VIDEO_RECORDS_PATH}/{datetime_object.strftime('%m-%d-%Y_%H-%M-%S')}.jpg"],
                                                                shell=False)
                print("[TAKE PHOTO]", "started")
            except Exception as err:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                print("[TAKE PHOTO]", err, exc_type, "line:", exc_tb.tb_lineno)

    def delete_video_records(self):
        os.system(f"sudo rm {self.VIDEO_RECORDS_PATH}/*")
        print("[DELETE VIDEO RECORDS] deleted video records")
