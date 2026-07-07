import time


class Timer:
    def __init__(self, frequency):
        self.frequency = frequency
        self.time_1 = 0
        self.time_2 = time.perf_counter()
        self.time_3 = time.perf_counter()
        self.exponential_average_cycle_time = 1 / frequency

    def wait(self):
        self.time_1 = time.perf_counter()

        spend_time = self.time_1 - self.time_3
        sleep_time = (1 / self.frequency) - spend_time

        if sleep_time > 0:
            time.sleep(sleep_time)

        self.time_2 = time.perf_counter()
        self.exponential_average_cycle_time = (0.9 * self.exponential_average_cycle_time) + (0.1 * (self.time_2 - self.time_3))

        self.time_3 = time.perf_counter()

    def get_average_cycle_time(self):
        return self.exponential_average_cycle_time

    def get_average_frequency(self):
        return 1 / self.exponential_average_cycle_time
