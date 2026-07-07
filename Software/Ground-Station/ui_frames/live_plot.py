import collections
import customtkinter
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class TkinterLivePlot:
    """ small live-updating line plot styled for the dark customtkinter theme """

    SURFACE_COLOR = "#2b2b2b"  # matches CTkFrame dark fg_color
    GRID_COLOR = "#3d3d3b"
    BASELINE_COLOR = "#4a4a47"
    TITLE_COLOR = "#c3c2b7"
    VALUE_COLOR = "#f2f2f2"
    TICK_COLOR = "#898781"
    THRESHOLD_COLOR = "#fab219"

    def __init__(self,
                 master,
                 width: int = 400,
                 height: int = 132,
                 title: str = "TkinterLivePlot",
                 unit: str = "",
                 length: int = 30,
                 line_color: str = "#3987e5",
                 value_format: str = "{:.2f}"):
        self.length = length
        self.line_color = line_color
        self.unit = unit
        self.value_format = value_format
        self.x_data = []
        self.y_data = collections.deque(maxlen=self.length)
        self.fill = None

        self.figure = Figure(figsize=(width / 90, height / 90), dpi=90, facecolor=self.SURFACE_COLOR)
        self.figure.subplots_adjust(top=0.80, bottom=0.10, left=0.15, right=0.97)
        self.axes = self.figure.add_subplot(1, 1, 1)
        self.axes.set_facecolor(self.SURFACE_COLOR)

        # recessive chrome: horizontal hairline grid, baseline only, muted ticks
        self.axes.grid(axis="y", color=self.GRID_COLOR, linewidth=0.8)
        self.axes.set_axisbelow(True)
        for side in ("top", "right", "left"):
            self.axes.spines[side].set_visible(False)
        self.axes.spines["bottom"].set_color(self.BASELINE_COLOR)
        self.axes.spines["bottom"].set_linewidth(0.8)
        self.axes.tick_params(axis="y", colors=self.TICK_COLOR, labelsize=8.5, length=0)
        self.axes.yaxis.set_major_locator(MaxNLocator(3))
        self.axes.get_xaxis().set_visible(False)
        self.axes.margins(y=0.18)

        # title on the left, live value readout on the right
        self.axes.set_title(title, loc="left", fontsize=10.5, color=self.TITLE_COLOR, pad=10)
        self.value_text = self.axes.text(1.0, 1.12, "–", transform=self.axes.transAxes,
                                         ha="right", va="bottom", fontsize=10.5, color=self.VALUE_COLOR)

        self.line, = self.axes.plot(self.x_data, self.y_data, linewidth=1.8,
                                    color=self.line_color, solid_capstyle="round", zorder=3)

        self.canvas = FigureCanvasTkAgg(self.figure, master=master)
        self.canvas.draw()

    def create_threshold_line(self, value):
        self.axes.axhline(value, ls=(0, (4, 3)), linewidth=1.1, color=self.THRESHOLD_COLOR, zorder=2)

    def add_data(self, value):
        if len(self.x_data) < self.length:
            self.x_data.append(len(self.x_data))
        self.y_data.append(value)

        self.line.set_data(self.x_data, self.y_data)
        self.value_text.set_text(f"{self.value_format.format(value)} {self.unit}".strip())

        if self.fill is not None:
            self.fill.remove()
            self.fill = None
        self.axes.relim()
        self.axes.autoscale_view(True, True, True)
        self.fill = self.axes.fill_between(self.x_data, list(self.y_data), self.axes.get_ylim()[0],
                                           color=self.line_color, alpha=0.12, linewidth=0, zorder=1)
        self.canvas.draw()

    def clear_data(self):
        self.x_data = []
        self.y_data = collections.deque(maxlen=self.length)
        self.line.set_data(self.x_data, self.y_data)
        if self.fill is not None:
            self.fill.remove()
            self.fill = None
        self.value_text.set_text("–")

    def place(self, **kwargs):
        self.canvas.get_tk_widget().place(**kwargs)

    def pack(self, **kwargs):
        self.canvas.get_tk_widget().pack(**kwargs)

    def grid(self, **kwargs):
        self.canvas.get_tk_widget().grid(**kwargs)


if __name__ == "__main__":
    customtkinter.set_appearance_mode("dark")
    app = customtkinter.CTk()

    plot_1 = TkinterLivePlot(app, title="Demo", unit="ms", value_format="{:.0f}")
    plot_1.pack(padx=10, pady=10)
    plot_1.create_threshold_line(15)

    for i in range(90):
        plot_1.add_data(i % 25)

    app.mainloop()
