import time
import hid
from typing import Tuple


class JoystickHandler:
    """ created for BETAFPV LiteRadio 2 SE (ExpressLRS 2.4GHz) """

    VENDOR_ID = 0x0483
    PRODUCT_ID = 0x572b
    EXP_ALPHA = 0.75  # exponential smoothing alpha factor
    STALE_TIMEOUT = 0.5  # seconds without a new report before treating the controller as disconnected

    def __init__(self):
        #                                                          arm               cam
        # values:                         roll pitch  yaw   thr   aux1  aux2  aux3  aux4
        self.values: list              = [1500, 1500, 1500, 1000, 1000, 1000, 1000, 1000]  # values are PWM values (1000-2000)
        self.disconnected_values: list = [1500, 1500, 1500, 1500, 1000, 1000, 1000, 1000]

        self.joystick = None
        self.last_report_time = None  # monotonic time of the last successful read

    def init_joystick(self):
        try:
            self.joystick = hid.device()
            self.joystick.open(vendor_id=self.VENDOR_ID, product_id=self.PRODUCT_ID)
        except Exception:
            self.joystick = None

    def get(self) -> Tuple[list, bool]:
        """ get list with joystick values and check for connect and disconnect """

        if self.joystick is None:
            self.init_joystick()
            return self.disconnected_values, False

        try:
            report = self.joystick.read(18, timeout_ms=20)
        except Exception:
            # actual read error -> controller was unplugged, try to reconnect
            self.joystick = None
            self.last_report_time = None
            self.init_joystick()
            return self.disconnected_values, False

        if report:
            # 11-bit HID values scaled to the 1000-2000 PWM range (0.48828125 = 500/1024)
            # roll, pitch, yaw, throttle (radio sends AETR channel order)
            self.values[0] = int(self.EXP_ALPHA * (((report[0] + 256 * report[1]) * 0.48828125) + 1000) + (1 - self.EXP_ALPHA) * self.values[0])
            self.values[1] = int(self.EXP_ALPHA * (((report[2] + 256 * report[3]) * 0.48828125) + 1000) + (1 - self.EXP_ALPHA) * self.values[1])
            self.values[2] = int(self.EXP_ALPHA * (((report[6] + 256 * report[7]) * 0.48828125) + 1000) + (1 - self.EXP_ALPHA) * self.values[2])
            self.values[3] = int(self.EXP_ALPHA * (((report[4] + 256 * report[5]) * 0.48828125) + 1000) + (1 - self.EXP_ALPHA) * self.values[3])

            # aux 1-4 (aux1 = arm switch, aux2 = alt/mag hold, aux3 = cam stab, aux4 = cam tilt)
            self.values[4] = int(((report[12] + 256 * report[13]) * 0.48828125) + 1000)
            self.values[5] = int(((report[10] + 256 * report[11]) * 0.48828125) + 1000)
            self.values[6] = int(((report[14] + 256 * report[15]) * 0.48828125) + 1000)
            self.values[7] = int(((report[8] + 256 * report[9]) * 0.48828125) + 1000) + 100  # +100 = gimbal servo trim

            self.last_report_time = time.monotonic()
            return self.values, True

        # empty read == no new report within the timeout, NOT a disconnect.
        # hold the last known values while the controller keeps sending; only
        # fall back to the safe disconnected values after a real silence.
        if self.last_report_time is not None and (time.monotonic() - self.last_report_time) < self.STALE_TIMEOUT:
            return self.values, True

        return self.disconnected_values, False


if __name__ == "__main__":
    joystick = JoystickHandler()
    while True:
        print("\r", joystick.get(), end="")
