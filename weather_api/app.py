# import requests


# def get_weather(city):

#     API_KEY = "86d8b721bfc8faf2d4bec2b8bd1f40a1"
#     URL = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"

#     try:
#         response = requests.get(URL)
#         data = response.json()
#         if response.status_code == 200:
#             print(f"Weather in {data['name']}: {data['sys']['country']}:")
#             print(f"Temperature: {data['main']['temp']}°C")
#             print(f"Humidity: {data['main']['humidity']}%")
#             print(f"Weather: {data['weather'][0]['description']}")
#             print(f"Wind Speed: {data['wind']['speed']} m/s")
#         else:
#             print(f"City {city} not found. Please check the city name.")
#     except requests.exceptions.RequestException as e:
#         print(f"Error: {e}")

# if __name__ == "__main__":
#     city = input("Enter the city name: ")
#     get_weather(city)



import customtkinter as ctk
import requests
from PIL import Image, ImageDraw
import io
import threading

# ── Theme ────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

API_KEY = "UR API KEY"
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

WEATHER_EMOJI = {
    "Clear": "☀️", "Clouds": "☁️", "Rain": "🌧️", "Drizzle": "🌦️",
    "Thunderstorm": "⛈️", "Snow": "❄️", "Mist": "🌫️", "Fog": "🌫️",
    "Haze": "🌫️", "Smoke": "💨", "Dust": "💨", "Tornado": "🌪️"
}

QUICK_CITIES = ["Mumbai", "Delhi", "Ranchi", "Bangalore", "London", "New York", "Tokyo"]


def wind_direction(deg):
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return dirs[round(deg / 45) % 8]


def humidity_label(h):
    if h < 30:   return "Very dry"
    if h < 50:   return "Comfortable"
    if h < 70:   return "Moderate"
    if h < 85:   return "Humid"
    return "Very humid"


def cloud_label(c):
    if c < 10:  return "Clear skies"
    if c < 30:  return "Mostly clear"
    if c < 60:  return "Partly cloudy"
    if c < 85:  return "Mostly cloudy"
    return "Overcast"


# ── App ───────────────────────────────────────────────────────────────────────
class WeatherApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("WeatherScope")
        self.geometry("520x760")
        self.resizable(False, False)
        self.configure(fg_color="#080d1a")

        self._build_ui()

    # ── UI Layout ─────────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=30, pady=(32, 0))

        ctk.CTkLabel(
            header_frame, text="WeatherScope",
            font=ctk.CTkFont(family="Helvetica", size=28, weight="bold"),
            text_color="#e8edf5"
        ).pack()
        ctk.CTkLabel(
            header_frame, text="Real-time weather data",
            font=ctk.CTkFont(size=13), text_color="#7a8899"
        ).pack(pady=(2, 0))

        # ── Search bar
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.pack(fill="x", padx=30, pady=(24, 0))

        self.city_entry = ctk.CTkEntry(
            search_frame, placeholder_text="Enter city name...",
            height=46, corner_radius=14,
            fg_color="#0e1627", border_color="#1e2d45", border_width=1,
            text_color="#e8edf5", placeholder_text_color="#7a8899",
            font=ctk.CTkFont(size=14)
        )
        self.city_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.city_entry.bind("<Return>", lambda e: self._fetch_threaded())

        self.search_btn = ctk.CTkButton(
            search_frame, text="Search", width=100, height=46,
            corner_radius=14, fg_color="#4f9eff", hover_color="#3a85e0",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._fetch_threaded
        )
        self.search_btn.pack(side="left")

        # ── Quick city chips
        chips_frame = ctk.CTkFrame(self, fg_color="transparent")
        chips_frame.pack(fill="x", padx=30, pady=(14, 0))

        for city in QUICK_CITIES:
            ctk.CTkButton(
                chips_frame, text=city, width=0, height=28,
                corner_radius=20, fg_color="#0e1627",
                border_color="#1e2d45", border_width=1,
                hover_color="#162038", text_color="#7a8899",
                font=ctk.CTkFont(size=12),
                command=lambda c=city: self._quick_search(c)
            ).pack(side="left", padx=(0, 7))

        # ── Status label (loading / error)
        self.status_label = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=13), text_color="#7a8899"
        )
        self.status_label.pack(pady=(16, 0))

        # ── Main weather card
        self.main_card = ctk.CTkFrame(
            self, corner_radius=20,
            fg_color="#0c1829", border_color="#1e2d45", border_width=1
        )
        self.main_card.pack(fill="x", padx=30, pady=(10, 0))
        self.main_card.pack_forget()

        # City + country
        top_row = ctk.CTkFrame(self.main_card, fg_color="transparent")
        top_row.pack(fill="x", padx=22, pady=(20, 0))

        self.lbl_city = ctk.CTkLabel(
            top_row, text="—",
            font=ctk.CTkFont(size=22, weight="bold"), text_color="#e8edf5"
        )
        self.lbl_city.pack(side="left")

        self.lbl_country = ctk.CTkLabel(
            top_row, text="—",
            font=ctk.CTkFont(size=12), text_color="#4f9eff",
            fg_color="#0e1f38", corner_radius=10
        )
        self.lbl_country.pack(side="left", padx=(10, 0), pady=2)

        # Temp + emoji
        temp_row = ctk.CTkFrame(self.main_card, fg_color="transparent")
        temp_row.pack(fill="x", padx=22, pady=(14, 0))

        self.lbl_temp = ctk.CTkLabel(
            temp_row, text="—",
            font=ctk.CTkFont(size=72, weight="bold"), text_color="#e8edf5"
        )
        self.lbl_temp.pack(side="left")

        ctk.CTkLabel(
            temp_row, text="°C",
            font=ctk.CTkFont(size=28), text_color="#7a8899"
        ).pack(side="left", anchor="s", pady=(0, 14))

        self.lbl_icon = ctk.CTkLabel(
            temp_row, text="🌤️", font=ctk.CTkFont(size=52)
        )
        self.lbl_icon.pack(side="right", padx=(0, 10))

        # Description + feels like
        self.lbl_desc = ctk.CTkLabel(
            self.main_card, text="—",
            font=ctk.CTkFont(size=14), text_color="#7a8899"
        )
        self.lbl_desc.pack(anchor="w", padx=24, pady=(2, 0))

        self.lbl_feels = ctk.CTkLabel(
            self.main_card, text="Feels like —°C",
            font=ctk.CTkFont(size=12), text_color="#5a6878"
        )
        self.lbl_feels.pack(anchor="w", padx=24, pady=(2, 0))

        # Min / Max / Visibility
        sep = ctk.CTkFrame(self.main_card, height=1, fg_color="#1e2d45")
        sep.pack(fill="x", padx=22, pady=(16, 0))

        mmv_row = ctk.CTkFrame(self.main_card, fg_color="transparent")
        mmv_row.pack(fill="x", padx=22, pady=(12, 18))

        self.lbl_min  = self._mini_stat(mmv_row, "MIN",  "—")
        self._vbar(mmv_row)
        self.lbl_max  = self._mini_stat(mmv_row, "MAX",  "—")
        self._vbar(mmv_row)
        self.lbl_vis  = self._mini_stat(mmv_row, "VISIBILITY", "—")

        # ── Stat grid (2×2)
        self.grid_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.grid_frame.pack(fill="x", padx=30, pady=(14, 0))
        self.grid_frame.pack_forget()

        self.grid_frame.columnconfigure((0, 1), weight=1)

        stats = [
            ("Humidity",   "humidity",   "%",    ""),
            ("Wind Speed", "wind",       " m/s", ""),
            ("Pressure",   "pressure",   " hPa", "Atmospheric"),
            ("Cloud Cover","clouds",     "%",    ""),
        ]
        self._stat_labels = {}
        for i, (label, key, unit, sub) in enumerate(stats):
            row, col = divmod(i, 2)
            card = ctk.CTkFrame(
                self.grid_frame, corner_radius=18,
                fg_color="#0c1829", border_color="#1e2d45", border_width=1
            )
            card.grid(row=row, column=col, padx=(0 if col else 0, 6 if col == 0 else 0),
                      pady=(0, 10), sticky="nsew",
                      ipadx=16, ipady=14)

            ctk.CTkLabel(
                card, text=f"● {label}",
                font=ctk.CTkFont(size=11), text_color="#4f9eff"
            ).pack(anchor="w", padx=16, pady=(14, 4))

            val_lbl = ctk.CTkLabel(
                card, text="—",
                font=ctk.CTkFont(size=26, weight="bold"), text_color="#e8edf5"
            )
            val_lbl.pack(anchor="w", padx=16)

            sub_lbl = ctk.CTkLabel(
                card, text=sub,
                font=ctk.CTkFont(size=11), text_color="#7a8899"
            )
            sub_lbl.pack(anchor="w", padx=16, pady=(2, 14))

            self._stat_labels[key] = (val_lbl, sub_lbl, unit)

        # Footer
        ctk.CTkLabel(
            self, text="Built with Python · OpenWeatherMap API",
            font=ctk.CTkFont(size=11), text_color="#2a3545"
        ).pack(pady=(18, 0))

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _mini_stat(self, parent, label, value):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(side="left", expand=True)
        ctk.CTkLabel(f, text=label, font=ctk.CTkFont(size=10),
                     text_color="#5a6878").pack()
        lbl = ctk.CTkLabel(f, text=value,
                            font=ctk.CTkFont(size=18, weight="bold"),
                            text_color="#e8edf5")
        lbl.pack()
        return lbl

    def _vbar(self, parent):
        ctk.CTkFrame(parent, width=1, height=36, fg_color="#1e2d45").pack(side="left")

    # ── Fetch ─────────────────────────────────────────────────────────────────
    def _quick_search(self, city):
        self.city_entry.delete(0, "end")
        self.city_entry.insert(0, city)
        self._fetch_threaded()

    def _fetch_threaded(self):
        self.search_btn.configure(state="disabled", text="...")
        self.status_label.configure(text="Fetching weather data…", text_color="#7a8899")
        self.main_card.pack_forget()
        self.grid_frame.pack_forget()
        threading.Thread(target=self._fetch_weather, daemon=True).start()

    def _fetch_weather(self):
        city = self.city_entry.get().strip()
        if not city:
            self.after(0, lambda: self._show_error("Please enter a city name."))
            return
        try:
            resp = requests.get(BASE_URL, params={
                "q": city, "appid": API_KEY, "units": "metric"
            }, timeout=8)
            data = resp.json()
            if resp.status_code == 200:
                self.after(0, lambda: self._update_ui(data))
            else:
                msg = data.get("message", "City not found.")
                self.after(0, lambda: self._show_error(f"Error: {msg.capitalize()}"))
        except requests.exceptions.ConnectionError:
            self.after(0, lambda: self._show_error("No internet connection."))
        except requests.exceptions.Timeout:
            self.after(0, lambda: self._show_error("Request timed out. Try again."))
        except Exception as e:
            self.after(0, lambda: self._show_error(f"Unexpected error: {e}"))

    def _show_error(self, msg):
        self.status_label.configure(text=f"⚠  {msg}", text_color="#ff6b6b")
        self.search_btn.configure(state="normal", text="Search")

    def _update_ui(self, d):
        main   = d["main"]
        wind   = d["wind"]
        clouds = d["clouds"]["all"]
        weather_main = d["weather"][0]["main"]

        self.lbl_city.configure(text=d["name"])
        self.lbl_country.configure(text=f"  {d['sys']['country']}  ")
        self.lbl_temp.configure(text=str(round(main["temp"])))
        self.lbl_icon.configure(text=WEATHER_EMOJI.get(weather_main, "🌤️"))
        self.lbl_desc.configure(text=d["weather"][0]["description"].capitalize())
        self.lbl_feels.configure(text=f"Feels like {round(main['feels_like'])}°C")
        self.lbl_min.configure(text=f"{round(main['temp_min'])}°")
        self.lbl_max.configure(text=f"{round(main['temp_max'])}°")
        vis = d.get("visibility")
        self.lbl_vis.configure(text=f"{vis/1000:.1f} km" if vis else "—")

        # Stat grid
        hum = main["humidity"]
        spd = wind["speed"]
        deg = wind.get("deg")
        pres = main["pressure"]

        updates = {
            "humidity": (f"{hum}%",    humidity_label(hum)),
            "wind":     (f"{spd:.1f} m/s", f"Dir: {wind_direction(deg)}" if deg is not None else "—"),
            "pressure": (f"{pres} hPa", "Atmospheric"),
            "clouds":   (f"{clouds}%",  cloud_label(clouds)),
        }
        for key, (val, sub) in updates.items():
            val_lbl, sub_lbl, _ = self._stat_labels[key]
            val_lbl.configure(text=val)
            sub_lbl.configure(text=sub)

        self.status_label.configure(text="")
        self.main_card.pack(fill="x", padx=30, pady=(10, 0))
        self.grid_frame.pack(fill="x", padx=30, pady=(14, 0))
        self.search_btn.configure(state="normal", text="Search")


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = WeatherApp()
    app.mainloop()