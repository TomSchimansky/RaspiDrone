import customtkinter


class StatusFrame(customtkinter.CTkFrame):
    """ right-side panel: system status indicators (left column) and telemetry values (right column) """

    ON_COLOR = "#7DCC50"
    OFF_COLOR = "#5f5f5c"
    HEADER_COLOR = "#c3c2b7"
    LABEL_COLOR = "#9a9a94"
    VALUE_COLOR = "#f2f2f2"
    CARD_COLOR = "#333333"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("corner_radius", 0)
        super().__init__(*args, **kwargs)
        self.grid_columnconfigure((0, 1), weight=1, uniform="cols")

        self.header_font = customtkinter.CTkFont(size=14, weight="bold")
        self.label_font = customtkinter.CTkFont(size=13)
        self.value_font = customtkinter.CTkFont(family="Menlo", size=13)

        # status column
        self.status_header = customtkinter.CTkLabel(self, text="Status", font=self.header_font,
                                                    text_color=self.HEADER_COLOR, anchor="w")
        self.status_header.grid(row=0, column=0, sticky="ew", padx=(20, 10), pady=(14, 4))

        self.status_card = customtkinter.CTkFrame(self, fg_color=self.CARD_COLOR, corner_radius=8)
        self.status_card.grid(row=1, column=0, sticky="nsew", padx=(20, 10), pady=(0, 14))
        self.status_card.grid_columnconfigure(1, weight=1)

        self.status_rows = {}
        for i, name in enumerate(["video stream", "video record", "GPS", "aruco system", "aruco position hold"]):
            dot = customtkinter.CTkLabel(self.status_card, text="●", width=16, font=self.label_font,
                                         text_color=self.OFF_COLOR)
            dot.grid(row=i, column=0, sticky="w", padx=(12, 2), pady=(8 if i == 0 else 2, 8 if i == 4 else 2))
            label = customtkinter.CTkLabel(self.status_card, text=name, font=self.label_font,
                                           text_color=self.LABEL_COLOR, anchor="w")
            label.grid(row=i, column=1, sticky="ew", padx=(0, 6))
            state = customtkinter.CTkLabel(self.status_card, text="OFF", font=self.value_font,
                                           text_color=self.OFF_COLOR, anchor="e", width=36)
            state.grid(row=i, column=2, sticky="e", padx=(0, 12))
            self.status_rows[name] = (dot, label, state)

        # values column
        self.values_header = customtkinter.CTkLabel(self, text="Values", font=self.header_font,
                                                    text_color=self.HEADER_COLOR, anchor="w")
        self.values_header.grid(row=0, column=1, sticky="ew", padx=(10, 20), pady=(14, 4))

        self.values_card = customtkinter.CTkFrame(self, fg_color=self.CARD_COLOR, corner_radius=8)
        self.values_card.grid(row=1, column=1, sticky="nsew", padx=(10, 20), pady=(0, 14))
        self.values_card.grid_columnconfigure(1, weight=1)

        self.value_rows = {}
        value_names = ["latitude", "longitude", "satellites", "CPU temp", "RAM load",
                       "control loop", "control rate", "data loop", "multiwii"]
        for i, name in enumerate(value_names):
            label = customtkinter.CTkLabel(self.values_card, text=name, font=self.label_font,
                                           text_color=self.LABEL_COLOR, anchor="w")
            label.grid(row=i, column=0, sticky="w", padx=(12, 6), pady=(8 if i == 0 else 1, 8 if i == len(value_names) - 1 else 1))
            value = customtkinter.CTkLabel(self.values_card, text="–", font=self.value_font,
                                           text_color=self.VALUE_COLOR, anchor="e")
            value.grid(row=i, column=1, sticky="e", padx=(0, 12))
            self.value_rows[name] = value

    def _set_status(self, name: str, value: bool):
        dot, label, state = self.status_rows[name]
        if value is True:
            dot.configure(text_color=self.ON_COLOR)
            state.configure(text="ON", text_color=self.ON_COLOR)
            label.configure(text_color=self.VALUE_COLOR)
        else:
            dot.configure(text_color=self.OFF_COLOR)
            state.configure(text="OFF", text_color=self.OFF_COLOR)
            label.configure(text_color=self.LABEL_COLOR)

    def set_video_stream_status(self, value: bool):
        self._set_status("video stream", value)

    def set_video_record_status(self, value: bool):
        self._set_status("video record", value)

    def set_gps_status(self, value: bool):
        self._set_status("GPS", value)

    def set_aruco_system_status(self, value: bool):
        self._set_status("aruco system", value)

    def set_aruco_position_hold_status(self, value: bool):
        self._set_status("aruco position hold", value)

    def set_position(self, lat: float, long: float):
        self.value_rows["latitude"].configure(text=f"{round(lat, 5)}")
        self.value_rows["longitude"].configure(text=f"{round(long, 5)}")

    def set_gps_satellites(self, value):
        self.value_rows["satellites"].configure(text=f"{value}")

    def set_cpu_temp(self, value):
        self.value_rows["CPU temp"].configure(text=f"{round(value, 1)} °C")

    def set_ram_load(self, value):
        self.value_rows["RAM load"].configure(text=f"{value} %")

    def set_control_loop_cycles(self, value):
        self.value_rows["control loop"].configure(text=f"{value} Hz")

    def set_control_cycles(self, value):
        self.value_rows["control rate"].configure(text=f"{value} Hz")

    def set_data_loop_cycles(self, value):
        self.value_rows["data loop"].configure(text=f"{value} Hz")

    def set_multiwii_cycles(self, value):
        if value is not None:
            self.value_rows["multiwii"].configure(text=f"{value} µs · {round(1 / (value / 1_000_000))} Hz")
        else:
            self.value_rows["multiwii"].configure(text="–")
