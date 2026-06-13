#!/usr/bin/env python3
"""
Weather CLI: Current conditions + 5-day forecast for any location.
Features:
  - Sunrise / sunset per day
  - Moon phase (computed locally)
  - High / low tide (from Open-Meteo Marine hourly tide_height over day's window)
  - Celsius or Fahrenheit (--celsius / --fahrenheit)
  - Dark-mode friendly palette (low-contrast, dimmed hues)
  - Uses Open-Meteo (no API key required)
"""

from __future__ import annotations
import sys
import json
import argparse
import urllib.request
import urllib.parse
from datetime import datetime, timezone, date as date_t


# ============================================================================
# ANSI color palette  — tuned for dark terminals (low contrast, muted hues)
# ============================================================================
class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"

    FG     = "\033[38;5;252m"      # near-white text
    DIMFG  = "\033[38;5;244m"      # subtle / dim text
    SLATE  = "\033[38;5;246m"      # borders / dividers
    SKY    = "\033[38;5;110m"
    TEAL   = "\033[38;5;108m"
    AMBER  = "\033[38;5;179m"
    SAGE   = "\033[38;5;108m"
    ROSE   = "\033[38;5;138m"
    LILAC  = "\033[38;5;139m"
    SAND   = "\033[38;5;101m"

    HDR_BG = "\033[48;5;237m"
    HL_BG  = "\033[48;5;238m"


def c(text: str, *codes: str) -> str:
    return "".join(codes) + text + C.RESET


def vw(s: str) -> int:
    """Visible width (emojis count as 2 columns). Strips ANSI when measuring."""
    out_w = 0
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == "\033" and i + 1 < len(s) and s[i + 1] == "[":
            j = s.find("m", i)
            if j != -1:
                i = j + 1
                continue
        if ord(ch) > 0x2600:
            out_w += 2
        else:
            out_w += 1
        i += 1
    return out_w


def strip_ansi(s: str) -> str:
    import re
    return re.sub(r"\033\[[0-9;]*m", "", s)


def widen(s: str, n: int, align: str = "<") -> str:
    pad = n - vw(s)
    if pad <= 0:
        return s
    if align == "<": return s + " " * pad
    if align == ">": return " " * pad + s
    lpad, rpad = pad // 2, pad - pad // 2
    return " " * lpad + s + " " * rpad


def hr(char: str = "─", width: int = 70, color: str = C.SLATE) -> str:
    return c(char * width, color)


# ============================================================================
# Weather code → emoji / label
# ============================================================================
ICON_MAP = {
    0:  ("☀️",  "Clear sky"),
    1:  ("🌤", "Mainly clear"),
    2:  ("⛅", "Partly cloudy"),
    3:  ("☁️", "Overcast"),
    45: ("🌫", "Fog"), 48: ("🌫", "Depositing rime fog"),
    51: ("🌦", "Light drizzle"), 53: ("🌦", "Moderate drizzle"), 55: ("🌧", "Dense drizzle"),
    56: ("🌧", "Light freezing drizzle"), 57: ("🌧", "Dense freezing drizzle"),
    61: ("🌦", "Light rain"), 63: ("🌧", "Moderate rain"), 65: ("🌧", "Heavy rain"),
    66: ("🌧", "Light freezing rain"), 67: ("🌧", "Heavy freezing rain"),
    71: ("🌨", "Light snow"), 73: ("🌨", "Moderate snow"), 75: ("❄️", "Heavy snow"),
    77: ("❄️", "Snow grains"),
    80: ("🌦", "Light rain showers"), 81: ("🌧", "Moderate rain showers"),
    82: ("⛈", "Heavy rain showers"),
    85: ("🌨", "Light snow showers"), 86: ("❄️", "Heavy snow showers"),
    95: ("⛈", "Thunderstorm"),
    96: ("⛈", "Thunderstorm w/ slight hail"),
    99: ("⛈", "Thunderstorm w/ heavy hail"),
}

def icon(code: int) -> str:
    return ICON_MAP.get(code, ("❔", "Unknown"))[0]

def label(code: int) -> str:
    return ICON_MAP.get(code, ("❔", "Unknown"))[1]


# ============================================================================
# Moon phase — local computation, no API
# ============================================================================
MOON_PHASES = [
    (0.00, "New"),            (0.03, "Waxing crescent"),
    (0.22, "First quarter"),  (0.47, "Waxing gibbous"),
    (0.50, "Full"),           (0.53, "Waning gibbous"),
    (0.78, "Last quarter"),   (0.97, "Waning crescent"),
    (1.01, "New"),
]
MOON_ICON = {
    "New": "🌑", "Waxing crescent": "🌒", "First quarter": "🌓",
    "Waxing gibbous": "🌔", "Full": "🌕", "Waning gibbous": "🌖",
    "Last quarter": "🌗", "Waning crescent": "🌘",
}

def moon_phase_for(day: date_t) -> tuple[str, str]:
    ref = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)
    cur = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    synodic = 29.530588853
    days = (cur - ref).total_seconds() / 86400.0
    phase = (days % synodic) / synodic
    for upper, name in MOON_PHASES:
        if phase < upper:
            return name, f"{phase * 100:.0f}%"
    return "New", "0%"


# ============================================================================
# Units
# ============================================================================
def c_to_f(t: float) -> float:
    return t * 9.0 / 5.0 + 32.0

def fmt_temp(t: float | None, units: str) -> str:
    if t is None: return "—"
    return f"{(c_to_f(t) if units == 'F' else t):.1f}°{units}"

def temp_color(t: float | None) -> str:
    if t is None: return C.DIMFG
    if t <= 0:    return C.SKY
    if t <= 15:   return C.TEAL
    if t <= 25:   return C.SAGE
    if t <= 32:   return C.AMBER
    return C.ROSE


# ============================================================================
# Network
# ============================================================================
def geocode(q: str) -> tuple[float, float, str]:
    url = "https://geocoding-api.open-meteo.com/v1/search?" + urllib.parse.urlencode({
        "name": q, "count": 1, "language": "en", "format": "json",
    })
    with urllib.request.urlopen(url, timeout=10) as r:
        d = json.load(r)
    if not d.get("results"):
        raise SystemExit(f"{c('✘', C.ROSE)} Location not found: {q!r}")
    t = d["results"][0]
    place = t["name"]
    region = t.get("admin1", "")
    country = t.get("country", "")
    full = f"{place}, {country}" if country else place
    if region and region != country:
        full += f" ({region})"
    return t["latitude"], t["longitude"], full


def fetch_weather(lat: float, lon: float) -> dict:
    url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode({
        "latitude": lat, "longitude": lon, "timezone": "auto", "forecast_days": 5,
        "current": ",".join([
            "temperature_2m", "relative_humidity_2m", "wind_speed_10m",
            "weather_code", "apparent_temperature", "is_day",
        ]),
        "daily": ",".join([
            "weather_code", "temperature_2m_max", "temperature_2m_min",
            "precipitation_sum", "precipitation_probability_max",
            "sunrise", "sunset", "uv_index_max", "wind_speed_10m_max",
        ]),
    })
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.load(r)


def fetch_tides_full(lat: float, lon: float) -> tuple[list[str], list[float | None]] | None:
    try:
        url = "https://marine-api.open-meteo.com/v1/marine?" + urllib.parse.urlencode({
            "latitude": lat, "longitude": lon, "timezone": "auto",
            "hourly": "sea_level_height_msl", "forecast_days": 5,
        })
        with urllib.request.urlopen(url, timeout=10) as r:
            d = json.load(r)
    except Exception:
        return None
    if not d.get("hourly"):
        return None
    return d["hourly"]["time"], d["hourly"].get("sea_level_height_msl", [])


# ============================================================================
# Rendering blocks
# ============================================================================
def banner(place: str, tz: str, lat: float, lon: float) -> str:
    title_pad = c("  WEATHER REPORT  ", C.BOLD, C.HDR_BG)
    coord = c(f"{lat:+.4f}, {lon:+.4f}", C.DIMFG)
    return "\n".join([
        "",
        hr(),
        f"{title_pad}  {c('·', C.DIM)}  {c(place, C.BOLD)}",
        f"{c('coords', C.DIMFG)} {coord}    {c('·', C.DIM)}    {c('tz', C.DIMFG)} {c(tz, C.FG)}",
        hr(),
    ])


def current_block(cur: dict, units: str) -> str:
    icon_str = icon(cur["weather_code"])
    cond     = label(cur["weather_code"])
    t        = cur["temperature_2m"]
    feels    = cur["apparent_temperature"]
    is_day   = cur.get("is_day", 1)

    label_now = c(" NOW ", C.BOLD, C.HL_BG) + " "
    dl = c("☀", C.AMBER) if is_day else c("🌙", C.SLATE)

    # pad the BARE label first, then color it — so escape codes never eat pad
    def lbl(text: str) -> str:
        return c(text.ljust(10), C.DIMFG)

    lines = [label_now + dl + "  " + c(f"{icon_str}  {cond}", C.BOLD, C.FG), ""]
    lines.append("  " + lbl("Temp") +
                 c(fmt_temp(t, units), C.BOLD, temp_color(t)) +
                 c("    feels ", C.DIM) + c(fmt_temp(feels, units), temp_color(feels)))
    lines.append("  " + lbl("Humidity") + c(f"{cur['relative_humidity_2m']}%", C.FG))
    lines.append("  " + lbl("Wind")     + c(f"{cur['wind_speed_10m']:.1f} km/h", C.FG))
    return "\n".join(lines)


def astronomy_tides_block(daily_today: dict | None, units: str, tide_full,
                          forecast_day: str | None) -> list[str]:
    """Returns ASTRONOMY + TIDES as separate lines with a blank line between them."""
    out: list[str] = []

    # ---- Astronomy
    if daily_today is not None:
        sunrise = daily_today.get("sunrise", ["—"])[0]
        sunset  = daily_today.get("sunset", ["—"])[0]
        try:
            sr = datetime.fromisoformat(sunrise).strftime("%H:%M")
            ss = datetime.fromisoformat(sunset).strftime("%H:%M")
            delta = datetime.fromisoformat(sunset) - datetime.fromisoformat(sunrise)
            dur_h = int(delta.total_seconds() // 3600)
            dur_m = int((delta.total_seconds() % 3600) // 60)
            dur = f"{dur_h}h {dur_m:02d}m"
        except Exception:
            sr, ss, dur = "—", "—", "—"

        today = datetime.now().date()
        pname, ppct = moon_phase_for(today)
        micon = MOON_ICON.get(pname, "🌙")

        def albl(text: str) -> str:
            return c(text.ljust(11), C.DIMFG)

        sr_c  = c(sr, C.AMBER)
        ss_c  = c(ss, C.LILAC)
        dur_c = c(dur, C.DIMFG)
        mp_c  = c(f"{micon} {pname} ({ppct} illuminated)", C.FG)

        a_header = c(" ASTRONOMY ", C.BOLD, C.HDR_BG) + " " + c(forecast_day or "", C.DIMFG)

        out.append("")           # blank line ABOVE the astronomy header
        out.append(a_header)
        out.append("  " + albl("Sunrise")  + sr_c +
                   "   " + albl("Sunset")  + ss_c +
                   "   " + albl("Daylight") + dur_c)
        out.append("  " + albl("Moon")     + mp_c)

    # ---- Tides (always preceded by a blank line so the blocks don't glue)
    if forecast_day:
        def tlbl(text: str) -> str:
            return c(text.ljust(6 if text == "High" else 5), C.DIMFG)

        t_header = c(" TIDES ", C.BOLD, C.HDR_BG) + " " + c(forecast_day, C.DIMFG)
        out.append("")           # explicit blank line between ASTRONOMY and TIDES
        out.append(t_header)
        if not tide_full:
            out.append("  " + c("Marine data unavailable for this location.", C.DIMFG))
        else:
            times, heights = tide_full
            pairs = [(t, h) for t, h in zip(times, heights)
                     if t.startswith(forecast_day) and h is not None]
            if not pairs:
                out.append("  " + c("No tide data for this date.", C.DIMFG))
            else:
                high = max(pairs, key=lambda x: x[1])
                low  = min(pairs, key=lambda x: x[1])
                hi_t = high[0].split("T")[1][:5]
                lo_t = low[0].split("T")[1][:5]
                out.append(
                    "  " + tlbl("High") +
                    c(f"{high[1]:.2f} m", C.FG) + c(f"  at  {hi_t}", C.DIMFG) +
                    "       " + tlbl("Low") +
                    c(f"{low[1]:.2f} m", C.FG) + c(f"  at  {lo_t}", C.DIMFG)
                )
    return out


def forecast_table(weather: dict, units: str, tide_full) -> list[str]:
    d = weather["daily"]

    # First pass: build rows (store ANSI-stripped text for the parts we widen)
    raw_rows: list[list[str]] = []   # visible text (no ANSI)
    styled_rows: list[list[str]] = [] # colored versions for printing
    for i, day in enumerate(d["time"]):
        dt = datetime.fromisoformat(day)
        day_text  = dt.strftime("%a %d-%b")
        icon_str  = icon(d["weather_code"][i])
        cond_text = label(d["weather_code"][i])
        hi = d["temperature_2m_max"][i]
        lo = d["temperature_2m_min"][i]
        hi_str = fmt_temp(hi, units)
        lo_str = fmt_temp(lo, units)
        rain_str = f"{d['precipitation_sum'][i]:.1f}mm"
        uv_str   = f"{d['uv_index_max'][i]:.1f}"
        sr = datetime.fromisoformat(d["sunrise"][i]).strftime("%H:%M")
        ss = datetime.fromisoformat(d["sunset"][i]).strftime("%H:%M")
        sun_str = f"{sr} → {ss}"

        # Tide text
        tide_str = "—"
        if tide_full:
            t_times, t_heights = tide_full
            day_pairs = [(t, h) for t, h in zip(t_times, t_heights)
                         if t.startswith(day) and h is not None]
            if day_pairs:
                high = max(day_pairs, key=lambda x: x[1])
                low  = min(day_pairs, key=lambda x: x[1])
                hi_t_str = high[0].split("T")[1][:5]
                lo_t_str = low[0].split("T")[1][:5]
                tide_str = f"{high[1]:.1f}m @ {hi_t_str} · {low[1]:.1f}m @ {lo_t_str}"

        raw_rows.append([day_text, f"{icon_str}  {cond_text}",
                         hi_str, lo_str, rain_str, uv_str, sun_str, tide_str])

        styled_rows.append([
            c(day_text, C.BOLD, C.FG),
            f"{icon_str}  {cond_text}",
            c(hi_str, temp_color(hi)),
            c(lo_str, temp_color(lo)),
            rain_str,
            uv_str,
            f"{c(sr, C.AMBER)} {c('→', C.DIM)} {c(ss, C.LILAC)}",
            _styled_tide_cell(tide_full, day) if tide_full else c("—", C.DIMFG),
        ])

    # Header texts (visible)
    headers_raw = ["Day", "Condition", "Hi", "Lo", "Rain", "UV",
                   "Sun (rise → set)", "Tide (Hi · Lo @ h:m)"]
    aligns = ["<", "<", ">", ">", ">", ">", "<", "<"]

    # Compute visible-width columns from header AND data (not from stripped ANSI)
    widths = []
    for col_i in range(len(headers_raw)):
        h_w = vw(headers_raw[col_i])
        c_w = max((vw(styled_rows[r_i][col_i]) for r_i in range(len(styled_rows))), default=0)
        # add 2 columns of padding around the cell
        widths.append(max(h_w, c_w) + 2)

    sep = "  "  # 2-space gutter between columns
    # Header line: bold-colored header text padded to widths
    head_cells = []
    for i in range(len(headers_raw)):
        padded_visible = headers_raw[i].ljust(widths[i]) if aligns[i] == "<" else headers_raw[i].rjust(widths[i])
        head_cells.append(c(padded_visible, C.BOLD))
    head_line = "  " + sep.join(head_cells)

    div_line = "  " + hr("─", sum(widths) + len(sep) * (len(widths) - 1) - len(sep), C.DIM)

    out = ["", c(" 5-DAY FORECAST ", C.BOLD, C.HDR_BG), "",
           head_line, div_line]

    for r in styled_rows:
        cells = [widen(r[i], widths[i], aligns[i]) for i in range(len(headers_raw))]
        out.append("  " + sep.join(cells))

    return out


def _styled_tide_cell(tide_full, day: str):
    times, heights = tide_full
    day_pairs = [(t, h) for t, h in zip(times, heights)
                 if t.startswith(day) and h is not None]
    if not day_pairs:
        return c("—", C.DIMFG)
    high = max(day_pairs, key=lambda x: x[1])
    low  = min(day_pairs, key=lambda x: x[1])
    hi_t = high[0].split("T")[1][:5]
    lo_t = low[0].split("T")[1][:5]
    return (f"{c(f'{high[1]:.1f}m', C.SAGE)} {c('@', C.DIM)} {c(hi_t, C.AMBER)}"
            f" {c('·', C.DIM)} "
            f"{c(f'{low[1]:.1f}m', C.SKY)} {c('@', C.DIM)} {c(lo_t, C.AMBER)}")


# ============================================================================
# Top-level formatting
# ============================================================================
def format_report(lat: float, lon: float, data: dict, units: str, tide_full) -> str:
    tz = data.get("timezone", "—")
    d0 = data.get("daily", {}) or {}
    today_date = d0.get("time", [None])[0] if d0.get("time") else None

    out: list[str] = []
    out.append(banner(place := data.get("name") or "", tz, data.get("latitude", lat), data.get("longitude", lon)))
    out.append(current_block(data["current"], units))
    out.extend(astronomy_tides_block(d0 if today_date else None, units, tide_full, today_date))
    out.append("")           # blank line between block and forecast table
    out.extend(forecast_table(data, units, tide_full))
    out.append("")
    out.append("  " + c("powered by Open-Meteo · no API key · dark-mode friendly palette", C.DIMFG))
    out.append("")
    return "\n".join(out)


# ============================================================================
# Main
# ============================================================================
def main():
    ap = argparse.ArgumentParser(description="Weather CLI with 5-day forecast, astronomy & tides.")
    ap.add_argument("location", help="City name, e.g. 'Tokyo'")
    ap.add_argument("--celsius", "--c", action="store_true", help="Display temperatures in °C (default)")
    ap.add_argument("--fahrenheit", "--f", action="store_true", help="Display temperatures in °F")
    ap.add_argument("--no-tides", action="store_true", help="Skip the marine API call")
    ap.add_argument("--raw", action="store_true", help="Disable color output (raw stdout not a tty)")
    args = ap.parse_args()

    units = "F" if args.fahrenheit else "C"
    if args.raw or not sys.stdout.isatty():
        for attr in ("RESET", "BOLD", "DIM",
                     "FG", "DIMFG", "SLATE", "SKY", "TEAL", "AMBER",
                     "SAGE", "ROSE", "LILAC", "SAND",
                     "HDR_BG", "HL_BG"):
            setattr(C, attr, "")

    lat, lon, place = geocode(args.location)
    data = fetch_weather(lat, lon)
    # bend the place into the data dict so banner can show it
    data["name"] = place
    tide_full = None if args.no_tides else fetch_tides_full(lat, lon)
    print(format_report(lat, lon, data, units, tide_full))


if __name__ == "__main__":
    main()
