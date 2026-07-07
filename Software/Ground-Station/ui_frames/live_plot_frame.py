import customtkinter
from .live_plot import TkinterLivePlot


class LivePlotFrame(customtkinter.CTkFrame):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("corner_radius", 0)
        super().__init__(*args, **kwargs)

        self.grid_rowconfigure((0, 1, 2, 3), weight=1)
        self.grid_columnconfigure(0, weight=1)

        # one fixed hue per metric (validated for the dark surface)
        self.ping_plot = TkinterLivePlot(self, title="Ping", unit="s", line_color="#3987e5", value_format="{:.3f}")
        self.ping_plot.grid(row=0, column=0, sticky="ns", pady=(6, 2))
        self.ping_plot.create_threshold_line(0.05)
        self.ping_plot_queue = []

        self.snr_plot = TkinterLivePlot(self, title="WiFi SNR", unit="dB", line_color="#199e70", value_format="{:.0f}")
        self.snr_plot.grid(row=1, column=0, sticky="ns", pady=2)
        self.snr_plot.create_threshold_line(20)
        self.snr_plot_queue = []

        self.control_error_plot = TkinterLivePlot(self, title="Control errors", unit="err/s", length=60,
                                                  line_color="#c98500", value_format="{:.0f}")
        self.control_error_plot.grid(row=2, column=0, sticky="ns", pady=2)
        self.control_error_plot_queue = []

        self.height_plot = TkinterLivePlot(self, title="Height", unit="cm", length=1000,
                                           line_color="#9085e9", value_format="{:.0f}")
        self.height_plot.grid(row=3, column=0, sticky="ns", pady=(2, 6))
        self.height_plot_queue = []

        self.after(500, self.live_plot_update_loop)

    def live_plot_update_loop(self):
        while len(self.ping_plot_queue) > 0:
            self.ping_plot.add_data(self.ping_plot_queue.pop(0))
        while len(self.snr_plot_queue) > 0:
            self.snr_plot.add_data(self.snr_plot_queue.pop(0))
        while len(self.control_error_plot_queue) > 0:
            self.control_error_plot.add_data(self.control_error_plot_queue.pop(0))
        while len(self.height_plot_queue) > 0:
            self.height_plot.add_data(self.height_plot_queue.pop(0))

        self.after(500, self.live_plot_update_loop)
