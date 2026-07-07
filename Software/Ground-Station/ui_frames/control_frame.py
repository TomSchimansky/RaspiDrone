import customtkinter


class ControlFrame(customtkinter.CTkFrame):

    HEADER_COLOR = "#c3c2b7"
    LABEL_COLOR = "#9a9a94"
    VALUE_COLOR = "#f2f2f2"
    ARMED_COLOR = "#d03b3b"
    ACTIVE_COLOR = "#7DCC50"
    BAR_COLOR = "#3987e5"

    BUTTON_WIDTH = 110
    BUTTON_WIDTH_WIDE = 2 * BUTTON_WIDTH + 8  # spans two button columns

    def __init__(self, master, app_reference, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.app_reference = app_reference

        self.header_font = customtkinter.CTkFont(size=14, weight="bold")
        self.label_font = customtkinter.CTkFont(size=13)
        self.value_font = customtkinter.CTkFont(family="Menlo", size=13)
        self.state_font = customtkinter.CTkFont(family="Menlo", size=13, weight="bold")
        self.aux_title_font = customtkinter.CTkFont(size=12)

        self.video_stream_frame = self._create_section(row=0, title="Video Stream", pady=(20, 12))
        self.video_stream_start_button = self._create_button(self.video_stream_frame, "start", 0, self.app_reference.start_video_stream)
        self.video_stream_stop_button = self._create_button(self.video_stream_frame, "stop", 1, self.app_reference.stop_video_stream)
        self.video_stream_open_button = self._create_button(self.video_stream_frame, "open stream", 2, self.app_reference.open_video_stream)
        self.video_stream_quality_menu = customtkinter.CTkOptionMenu(self.video_stream_frame, values=["low", "medium", "HD", "FullHD"],
                                                                     width=self.BUTTON_WIDTH, font=self.label_font)
        self.video_stream_quality_menu.grid(row=1, column=3, padx=(8, 12), pady=(0, 12))

        self.video_record_frame = self._create_section(row=1, title="Video Record")
        self.video_record_start_button = self._create_button(self.video_record_frame, "start", 0, self.app_reference.start_video_record)
        self.video_record_stop_button = self._create_button(self.video_record_frame, "stop", 1, self.app_reference.stop_video_record)
        self.take_photo_button = self._create_button(self.video_record_frame, "take photo", 2, self.app_reference.take_photo)
        self.download_button = self._create_button(self.video_record_frame, "download", 3, self.app_reference.download_video_record)
        self.delete_button = self._create_button(self.video_record_frame, "delete", 4, self.app_reference.delete_video_records)

        # joystick section: stick channels with bars + values, aux channels with their meaning
        self.joystick_frame = self._create_section(row=2, title="Joystick")
        self.joystick_frame.grid_columnconfigure((2, 5), weight=1)

        self.channel_bars = {}
        self.channel_values = {}
        for name, row, col in (("throttle", 1, 0), ("yaw", 2, 0), ("pitch", 1, 3), ("roll", 2, 3)):
            text = customtkinter.CTkLabel(self.joystick_frame, text=name, width=70, anchor="w",
                                          font=self.label_font, text_color=self.LABEL_COLOR)
            text.grid(row=row, column=col, padx=(12, 0), pady=(0, 8))
            bar = customtkinter.CTkProgressBar(self.joystick_frame, width=110, progress_color=self.BAR_COLOR)
            bar.set(0.5)
            bar.grid(row=row, column=col + 1, pady=(0, 8))
            value = customtkinter.CTkLabel(self.joystick_frame, text="1500", width=48, anchor="e",
                                           font=self.value_font, text_color=self.VALUE_COLOR)
            value.grid(row=row, column=col + 2, padx=(6, 12), pady=(0, 8), sticky="w")
            self.channel_bars[name] = bar
            self.channel_values[name] = value

        # aux channels with what they actually control (multiwii box assignment)
        self.aux_row = customtkinter.CTkFrame(self.joystick_frame, fg_color="transparent")
        self.aux_row.grid(row=3, column=0, columnspan=6, sticky="ew", padx=12, pady=(2, 10))
        self.aux_row.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="aux")
        self.aux_states = {}
        for i, (aux, meaning) in enumerate((("aux-1", "arm"), ("aux-2", "alt/mag hold"),
                                            ("aux-3", "cam stab"), ("aux-4", "cam tilt"))):
            title = customtkinter.CTkLabel(self.aux_row, text=f"{aux} · {meaning}", anchor="w",
                                           font=self.aux_title_font, text_color=self.LABEL_COLOR)
            title.grid(row=0, column=i, sticky="w", padx=(0, 8))
            state = customtkinter.CTkLabel(self.aux_row, text="–", anchor="w", font=self.state_font,
                                           text_color=self.LABEL_COLOR)
            state.grid(row=1, column=i, sticky="w", padx=(0, 8))
            self.aux_states[aux] = state

        self.joystick_value_list = None
        self.after(100, self.joystick_value_update_loop)

        self.callibration_frame = self._create_section(row=3, title="Calibration")
        self.calibrate_magnetometer_button = self._create_button(self.callibration_frame, "calibrate magnetometer", 0,
                                                                 self.app_reference.calibrate_magnetometer, width=self.BUTTON_WIDTH_WIDE)
        self.calibrate_accelerometer_button = customtkinter.CTkButton(self.callibration_frame, text="calibrate accelerometer",
                                                                      width=self.BUTTON_WIDTH_WIDE, font=self.label_font,
                                                                      command=self.app_reference.calibrate_accelerometer)
        self.calibrate_accelerometer_button.grid(row=1, column=1, padx=(8, 12), pady=(0, 12))

        self.raspberrypi_frame = self._create_section(row=4, title="RaspberryPi")
        self.stop_program_button = self._create_button(self.raspberrypi_frame, "stop program", 0, self.app_reference.stop_program)
        self.reboot_button = self._create_button(self.raspberrypi_frame, "reboot", 1, self.app_reference.reboot)

        self.aruco_frame = self._create_section(row=5, title="Aruco Position Hold")
        self.aruco_start_button = self._create_button(self.aruco_frame, "start", 0, None)
        self.aruco_stop_button = self._create_button(self.aruco_frame, "stop", 1, None)

    def _create_section(self, row: int, title: str, pady=(0, 12)) -> customtkinter.CTkFrame:
        frame = customtkinter.CTkFrame(self)
        frame.grid(row=row, column=0, sticky="ew", padx=20, pady=pady)
        header = customtkinter.CTkLabel(frame, text=title, anchor="w", font=self.header_font,
                                        text_color=self.HEADER_COLOR)
        header.grid(row=0, column=0, sticky="w", padx=12, pady=(8, 6), columnspan=3)
        return frame

    def _create_button(self, section, text: str, column: int, command, width: int = None) -> customtkinter.CTkButton:
        button = customtkinter.CTkButton(section, text=text, width=width or self.BUTTON_WIDTH,
                                         font=self.label_font, command=command)
        button.grid(row=1, column=column, padx=(12, 0) if column == 0 else (8, 0), pady=(0, 12))
        return button

    def set_joystick_values(self, value_list: list):
        """ gets list of [roll, pitch, yaw, throttle, aux1, aux2, aux3, aux4] with values from 1000 to 2000 """
        self.joystick_value_list = value_list

    def joystick_value_update_loop(self):
        if self.joystick_value_list is not None:
            v = self.joystick_value_list
            for name, index in (("roll", 0), ("pitch", 1), ("yaw", 2), ("throttle", 3)):
                self.channel_bars[name].set((v[index] - 1000) / 1000)
                self.channel_values[name].configure(text=f"{v[index]}")

            # aux-1: arm switch (multiwii ARM + ANGLE box on MID/HIGH)
            if v[4] >= 1300:
                self.aux_states["aux-1"].configure(text="ARMED", text_color=self.ARMED_COLOR)
            else:
                self.aux_states["aux-1"].configure(text="disarmed", text_color=self.LABEL_COLOR)

            # aux-2: BARO box on MID/HIGH, MAG box on HIGH
            if v[5] >= 1700:
                self.aux_states["aux-2"].configure(text="baro+mag", text_color=self.ACTIVE_COLOR)
            elif v[5] >= 1300:
                self.aux_states["aux-2"].configure(text="baro", text_color=self.ACTIVE_COLOR)
            else:
                self.aux_states["aux-2"].configure(text="off", text_color=self.LABEL_COLOR)

            # aux-3: CAMSTAB box on HIGH
            if v[6] >= 1700:
                self.aux_states["aux-3"].configure(text="on", text_color=self.ACTIVE_COLOR)
            else:
                self.aux_states["aux-3"].configure(text="off", text_color=self.LABEL_COLOR)

            # aux-4: proportional camera tilt
            self.aux_states["aux-4"].configure(text=f"{round((v[7] - 1000) / 10)} %", text_color=self.VALUE_COLOR)

        self.after(100, self.joystick_value_update_loop)
