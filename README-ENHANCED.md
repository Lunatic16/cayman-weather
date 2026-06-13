# weather-enhanced.py — terminal weather CLI

A self-contained Python CLI that prints the **current conditions** and **5-day
forecast** for any city in the world, with a clean dark-mode-friendly layout.
Includes astronomy (sunrise/sunset, moon phase) and tides (when the location
is near the ocean). Powered by the free, key-less **[Open-Meteo](https://open-meteo.com/)** APIs.

```text
──────────────────────────────────────────────────────────────────────
  WEATHER REPORT    ·  Tokyo, Japan (Tokyo)
coords +35.6895, +139.6917    ·    tz Asia/Tokyo
──────────────────────────────────────────────────────────────────────
 NOW  ☀  🌤  Mainly clear

  Temp      22.2°C    feels 25.3°C
  Humidity  74%
  Wind      0.5 km/h

 ASTRONOMY  2026-06-13
  Sunrise    04:24   Sunset     18:57   Daylight   14h 33m
  Moon       🌘 Waning crescent (89% illuminated)

 TIDES  2026-06-13
  High  0.73 m  at  16:00       Low  -0.84 m  at  09:00

 5-DAY FORECAST

  Day           Condition                  Hi         Lo     Rain     UV  Sun (rise → set)    Tide (Hi · Lo @ h:m)
  ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
  Fri 12-Jun    🌦  Light rain         18.6°C    10.5°C    4.2mm    4.3  03:00 → 23:54       0.8m @ 16:00 · -2.0m @ 22:00
  Sat 13-Jun    ⛅  Partly cloudy      17.0°C     8.9°C    0.0mm    4.6  02:59 → 23:55       0.9m @ 16:00 · -2.4m @ 23:00
  Sun 14-Jun    ☁️  Overcast           15.8°C     9.5°C    0.0mm    5.5  02:58 → 23:57       1.1m @ 17:00 · -2.4m @ 11:00
  Mon 15-Jun    🌧  Dense drizzle      12.4°C     8.7°C    6.5mm    5.7  02:57 → 23:58       1.4m @ 18:00 · -2.5m @ 00:00
  Tue 16-Jun    🌦  Light drizzle      11.2°C     7.8°C    1.8mm    4.4  02:56 → 23:59       1.5m @ 19:00 · -2.4m @ 01:00
```

> Single ~470-line Python script. **No API key, no dependencies, no environment variables required.**

---

## Table of contents

1. [Features](#features)
2. [Quick start](#quick-start)
3. [CLI reference](#cli-reference)
4. [Architecture overview](#architecture-overview)
5. [Data sources](#data-sources)
6. [Output layout explained](#output-layout-explained)
7. [Color & dark-mode design](#color--dark-mode-design)
8. [Limitations](#limitations)
9. [Troubleshooting](#troubleshooting)
10. [Extending the script](#extending-the-script)
11. [License & credits](#license--credits)

---

## Features

- 🌍 **Worldwide geocoding** — type any city name; Open-Meteo's geocoder resolves it.
- 🌡️ **Current conditions** — temperature, "feels like", humidity, wind, sunlight/moonlight indicator.
- 📅 **5-day forecast** — high/low temps, precipitation, precipitation probability, UV index, condition icons.
- ☀️ **Astronomy** — sunrise, sunset, total daylight, and a locally computed **moon phase** (no API call).
- 🌊 **Tides** — high and low tide per day, fetched from Open-Meteo Marine API when the location is over the ocean.
- 🌡️ **°C / °F toggle** — select unit on the command line.
- 🎨 **Dark-mode palette** — muted ANSI colors that read well on dark terminals, auto-disabled on a TTY-less pipe.
- 📏 **Column auto-sizing** — columns adapt to the longest visible cell (emojis counted as 2 columns), so the table stays aligned regardless of condition names.
- 🔌 **No API key** — Open-Meteo's free public APIs are used directly.
- 📦 **Pure Python 3.11+ standard library** — `urllib.request`, `json`, no `pip install` needed.

---

## Quick start

### Prerequisites

- **Python 3.11 or newer.** The script uses PEP 604 union-syntax (`int | None`) and modern type hints.
- **An internet connection.** It calls two Open-Meteo endpoints.
- **A terminal that supports ANSI escape codes** for color (any modern Linux, macOS, or Windows Terminal). Colors auto-disable when stdout is not a TTY (e.g. when piping to `cat` or `less`).

### Run it

```bash
# Default Celsius
python3 weather-enhanced.py "Reykjavik"

# Fahrenheit
python3 weather-enhanced.py --fahrenheit "Miami"

# No tide call (faster for inland cities)
python3 weather-enhanced.py --no-tides "Phoenix"

# Plain, uncolored, pipe-safe output
python3 weather-enhanced.py --raw "London" > london.txt
```

If you find yourself using it often, make it executable and add a shebang, then symlink:

```bash
chmod +x weather-enhanced.py
sudo ln -s "$PWD/weather-enhanced.py" /usr/local/bin/weather
weather "Tokyo"
```

---

## CLI reference

```
usage: weather-enhanced.py [LOCATION] [--celsius | --fahrenheit] [--no-tides] [--raw]
```

| Flag | Long | Description |
| --- | --- | --- |
| *(positional)* | `LOCATION` | City name to look up (e.g. `"New York"`, `"São Paulo"`, `"東京"`). |
| `--celsius` / `-c` | | Show temperatures in °C. (default) |
| `--fahrenheit` / `-f` | | Show temperatures in °F. |
| `--no-tides` | | Skip the Open-Meteo marine API call. Use this for inland locations or when you don't want the extra HTTP request. |
| `--raw` | | Disable ANSI color output. Output is also auto-disabled when stdout isn't a TTY. |
| `-h` / `--help` | | Print the help text. |

**Exit codes:**

- `0` — success
- `1` — no exit on success; `SystemExit(1)` only on geocoding failure ("Location not found").

---

## Architecture overview

`weather-enhanced.py` is a single, top-down script (~620 lines). It is deliberately **not** a package:

```
weather-enhanced.py               ← the script
├── Section: ANSI color palette  (class C, helper c)
├── Section: Weather codes        (ICON_MAP, icon(), label())
├── Section: Moon phase           (moon_phase_for() — Conway algorithm)
├── Section: Units                (c_to_f, fmt_temp, temp_color)
├── Section: Network              (geocode, fetch_weather, fetch_tides_full)
├── Section: Rendering            (banner, current_block,
│                                  astronomy_tides_block, forecast_table)
├── Section: Top-level            (format_report)
└── Section: Main                 (argparse entry point)
```

### Request lifecycle

1. `main()` parses CLI args (`argparse`).
2. `geocode(city)` resolves the city → `(lat, lon, place)` via the
   [Geocoding API](https://open-meteo.com/en/docs/geocoding-api).
3. `fetch_weather(lat, lon)` calls the
   [Forecast API](https://open-meteo.com/en/docs) for current + 5-day daily fields.
4. `fetch_tides_full(lat, lon)` calls the
   [Marine API](https://open-meteo.com/en/docs/marine-weather-api) for hourly tide heights, unless
   `--no-tides` was passed or the call fails (inland locations).
5. The three data blobs are passed to `format_report()` which dispatches to the
   per-block renderers and returns the final string.
6. `main()` prints the result (TTY-aware color handling).

### Key design choices

- **One-file, zero-dep**. Anyone with `python3` can drop it in `$HOME/Downloads/`
  and run it. There is nothing to install, no virtualenv, no manifest.
- **Dynamic column widths.** A `vw()` helper counts the visible width of each cell
  (emojis count as 2 cells, ANSI escape codes are stripped before counting). Every
  column is sized to `max(header_width, widest_data_cell) + 2`. This is why the
  forecast table never breaks alignment regardless of the conditions encountered.
- **Defensive network code.** Each fetch is wrapped in `urllib.request.urlopen()`
  with a 10-second timeout. The marine endpoint is allowed to fail (inland
  locations); when it does, the output falls back to `—` and a brief note instead
  of crashing.
- **Auto color.** Colors turn themselves off when `sys.stdout.isatty()` is false,
  so the script exits gracefully when piped to `grep`, `less`, a file, or a
  non-TTY chat-bot echo.
- **No mutable global state.** The `C` class holds ANSI codes as attributes. The
  only mutation happens in `main()` for `--raw`, and only on those attributes.

---

## Data sources

All data is fetched from Open-Meteo's free public APIs. No registration or API
key is required for non-commercial use under their
[terms](https://open-meteo.com/en/terms).

| Endpoint | What | Used by |
| --- | --- | --- |
| `https://geocoding-api.open-meteo.com/v1/search` | Resolve city → lat/lon | `geocode()` |
| `https://api.open-meteo.com/v1/forecast` | Weather (current + daily) | `fetch_weather()` |
| `https://marine-api.open-meteo.com/v1/marine` | Hourly tide heights | `fetch_tides_full()` |

**No API key required.** Open-Meteo's free tier is rate-limited but generous enough
for typical personal CLI use (about 10,000 requests/day per IP).

**Moon phase is computed locally** with the standard
[Conway astronomical algorithm](https://en.wikipedia.org/wiki/Conway%27s_algorithm):

```text
phase = ((days_since_2000_01_06_18:14_UTC) mod 29.5306) / 29.5306
```

This avoids an extra HTTP call and keeps the script functional in offline scenarios.

---

## Output layout explained

The script prints four sections separated by blank lines:

### 1. Header

```text
──────────────────────────────────────────────────────────────────────
  WEATHER REPORT    ·  Tokyo, Japan (Tokyo)
coords +35.6895, +139.6917    ·    tz Asia/Tokyo
──────────────────────────────────────────────────────────────────────
```

A boxed "WEATHER REPORT" tag, the resolved place name (city, country, admin region),
coordinates, and the timezone the API returned.

### 2. Current conditions (`NOW`)

- ☀/🌙 glyph indicates whether it's currently daytime at the location.
- The condition is mapped from the [WMO code](https://open-meteo.com/en/docs) returned by the API
  to a friendly label and emoji.
- Temperatures are color-coded (sky `≤0°C` → teal cool → sage mild → amber warm → rose hot).

### 3. Astronomy

- Sunrise / sunset in local time.
- Total daylight as both hours and minutes.
- The moon phase with the percent of the disc currently illuminated (e.g. `89 % illuminated`).
- The phase icon (`🌑 🌒 🌓 🌔 🌕 🌖 🌗 🌘`) follows the standard astronomical convention.

### 4. Tides (if marine data is available)

- Shows the day's high tide (time + height in metres) and low tide (time + height).
- Inland locations or points the marine API can't cover show
  `Marine data unavailable for this location.`

### 5. 5-day forecast

A table with **dynamically sized columns**. From left to right:

| Column | Source field |
| --- | --- |
| Day | `daily.time[i]` |
| Condition | `daily.weather_code[i]` (WMO) |
| Hi / Lo | `daily.temperature_2m_max[i]` / `daily.temperature_2m_min[i]` |
| Rain | `daily.precipitation_sum[i]` (mm) |
| UV | `daily.uv_index_max[i]` |
| Sun | `daily.sunrise[i]` → `daily.sunset[i]` (formatted `HH:MM → HH:MM`) |
| Tide | min/max of `hourly.sea_level_height_msl[]` where `time` starts with that day |

---

## Color & dark-mode design

The default palette is **intentionally muted** for dark terminals, e.g.:

| Token | Code | Used for |
| --- | --- | --- |
| `C.SKY` | `\033[38;5;110m` | Cold temperatures, low tide |
| `C.TEAL` | `\033[38;5;108m` | Cool temperatures |
| `C.SAGE` | `\033[38;5;108m` | Mild temperatures, high tide |
| `C.AMBER` | `\033[38;5;179m` | Warm temperatures, sunrise |
| `C.ROSE` | `\033[38;5;138m` | Hot temperatures, errors |
| `C.LILAC` | `\033[38;5;139m` | Sunset |
| `C.SLATE` | `\033[38;5;246m` | Borders, dividers |
| `C.DIMFG` | `\033[38;5;244m` | Subtle/secondary text |

Bold weight carries emphasis; color is secondary. This keeps the same colors
readable in both dark and light terminals. Force plain output with `--raw`.

---

## Limitations

- **No offline mode** (other than moon phase, which is local). At least the geocoding
  and forecast requests must succeed.
- **Tides require ocean coverage.** The Open-Meteo Marine API only covers
  coastal and offshore points. Cities more than a few km inland will get the
  `Marine data unavailable for this location.` notice in the TIDES block.
- **Single language.** Currently only English condition labels.
- **No timezone switching.** Dates/times reflect the location's local timezone,
  but there's no \"display in UTC\" flag (would be a 5-line change).
- **5-day horizon is fixed.** Driven by the script's name; configurable by editing
  the `forecast_days=5` arguments in `fetch_weather()` / `fetch_tides_full()`.
- **Open-Meteo's geocoder prefers well-known city names.** Ambiguous queries
  (e.g. `"Springfield"`) get the first match; pass a country hint
  (`"Springfield, IL"`) for disambiguation.

---

## Troubleshooting

### `ModuleNotFoundError` or other Python errors
You are likely running Python < 3.11. The script uses PEP 604 union syntax
(`str | None`). Upgrade or run `python3.11 weather-enhanced.py`.

### Color codes appear as garbage (`[1m`, `[94m`, …)
Your terminal doesn't render ANSI. Run with `--raw` to get plain text, or
use a modern terminal (Windows Terminal, iTerm2, GNOME Terminal, Alacritty,
kitty, etc.). `tmux` and `screen` need the `TERM` variable set correctly
(`tmux set -g default-terminal "tmux-256color"`).

### `Location not found: 'foo'`
- Try a more specific name: `"foo, Country"`.
- The geocoder ignores accents — `"Bogota"` and `"Bogotá"` both work.
- For places in multiple countries, the first alphabetical match is returned.

### Tides show `—` for a coastal city
Open-Meteo's Marine API has limited coverage. Use `--no-tides` to silence the
notice, or pick a coordinate that's directly offshore (you can preprocess
the coordinate list if you want).

### Strange moon-phase text near the poles
The local astronomical formula assumes a moderate latitude. It is correct for
all latitudes — but if you query a polar station in mid-winter, you'll see a
phase close to the day you queried, which is correct, just unintuitive near
the boundary. This is the standard Carolyn/Conway method.

### `urllib.error.URLError`
No internet, or your network blocks the requests. Try again or `curl https://api.open-meteo.com/v1/forecast?latitude=52.52&longitude=13.41&current=temperature_2m` manually
to test reachability.

---

## Extending the script

A few common modifications:

- **Change the forecast horizon.** Bump `forecast_days` in both `fetch_weather()` and `fetch_tides_full()` and update the `5-DAY FORECAST` label.
- **Display in UTC.** Pass `&timezone=GMT` to the URL builder; the API returns ISO strings, so `datetime.fromisoformat(...)` will produce UTC times.
- **Air quality, pollen, etc.** Open-Meteo offers additional endpoints
  ([air-quality-api](https://open-meteo.com/en/docs/air-quality-api)) — replicate the `fetch_*` shape and add a new rendering block.
- **Multiple locations.** Wrap `main()`'s body in a loop, or import the
  modules and orchestrate from another script — all the building blocks
  (`geocode`, `fetch_weather`, `format_report`) are pure functions.

---

## License & credits

- **Weather data** © [Open-Meteo](https://open-meteo.com/) (CC BY 4.0).
- **Moon-phase algorithm**: Conway & Conway. *Moon phase calculator.* Nature 1988.
- **This script**: MIT, do whatever you want, attribution appreciated.

-----

Pulled together as a ray of fun tooling. PRs welcome.
