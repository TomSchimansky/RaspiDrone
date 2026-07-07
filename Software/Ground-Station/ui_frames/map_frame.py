import customtkinter
import tkintermapview


class MapFrame(customtkinter.CTkFrame):
    def __init__(self, master, app_reference, *args, **kwargs):
        kwargs.setdefault("corner_radius", 0)
        super().__init__(master, *args, **kwargs)
        self.app_reference = app_reference
        self.grid_columnconfigure(2, weight=1)
        self.rowconfigure(0, weight=1)

        self.map_view = tkintermapview.TkinterMapView(self, width=400, database_path=self.app_reference.map_database)
        self.map_view.grid(row=0, column=0, columnspan=3, sticky="nsew")
        self.map_view_marker = self.map_view.set_position(0, 0, marker=True)
        self.map_view.set_zoom(0)
        self.map_view.set_tile_server("https://mt0.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={z}&s=Ga", max_zoom=21)

        self.focus_button = customtkinter.CTkButton(self, text="focus", width=100, command=self.focus_target)
        self.focus_button.grid(row=1, column=0, padx=10, pady=10)

        self.follow_checkbox = customtkinter.CTkCheckBox(self, text="follow")
        self.follow_checkbox.grid(row=1, column=1, padx=10, pady=10)

    def focus_target(self):
        self.map_view.set_position(*self.map_view_marker.position)

    def set_target_position(self, lat, long):
        self.map_view_marker.set_position(lat, long)
        if self.follow_checkbox.get() == 1:
            self.focus_target()


