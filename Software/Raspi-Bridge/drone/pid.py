

class PID:
    def __init__(self, p=0.2, i=0.0, d=0.0, current_time=None):

        self.Kp = p  # PID constants
        self.Ki = i
        self.Kd = d

        self.sample_time = 0.00
        self.last_time = current_time

        self.PTerm = 0.0
        self.ITerm = 0.0
        self.DTerm = 0.0
        self.last_error = 0.0

        self.windup_guard = 20.0

        self.output = 0.0
        self.point = 0.0

    def set_point(self, value):
        self.point = value

    def get_output(self):
        return self.output

    def get_point(self):
        return self.point

    def set_windup(self, windup):
        self.windup_guard = windup

    def set_sample_time(self, sample_time):
        self.sample_time = sample_time

    def reset_time(self):
        self.last_time = None

    def update(self, feedback_value, current_time):

        if self.last_time is None:
            self.last_time = current_time

        delta_time = current_time - self.last_time

        if delta_time >= self.sample_time:

            error = self.point - feedback_value
            delta_error = error - self.last_error

            self.PTerm = self.Kp * error
            self.ITerm += error * delta_time
            self.DTerm = 0.0
            if delta_time > 0:
                self.DTerm = delta_error / delta_time

            if self.ITerm < -self.windup_guard:
                self.ITerm = -self.windup_guard
            elif self.ITerm > self.windup_guard:
                self.ITerm = self.windup_guard

            self.last_time = current_time
            self.last_error = error

            self.output = self.PTerm + (self.Ki * self.ITerm) + (self.Kd * self.DTerm)