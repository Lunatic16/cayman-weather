# Cayman Islands Weather Script

A production-ready bash script that displays the current date, time, and live weather conditions for the Cayman Islands (George Town).

## Key Features

- 🕐 **Real-time clock** — Cayman Islands timezone (America/Cayman, EST/UTC-5)
- 🌤️ **Live weather data** — Temperature, humidity, wind speed, and conditions via Open-Meteo API
- 🌡️ **Unit toggle** — Celsius (default) or Fahrenheit (`--fahrenheit`)
- 🎨 **TTY-aware** — Colored output in terminals, plain text when piped
- 🔍 **Debug mode** — Verbose logging with `--verbose` for troubleshooting
- 🛡️ **Defensive programming** — Strict mode, dependency checks, proper exit codes
- ✅ **Shellcheck clean** — Zero warnings on static analysis

---

## Tech Stack

- **Language**: Bash 4.0+
- **Runtime**: POSIX-compatible shell (bash, zsh)
- **HTTP Client**: `curl`
- **JSON Parser**: `python3` (for weather data parsing)
- **Weather API**: [Open-Meteo](https://open-meteo.com/) (free, no API key required)

---

## Prerequisites

| Tool     | Version | Required | Purpose                    |
|----------|---------|----------|----------------------------|
| `bash`   | 4.0+    | ✅ Yes   | Script runtime             |
| `curl`   | 7.0+    | ✅ Yes   | HTTP requests to API       |
| `python3`| 3.6+    | ⚠️ Recommended | JSON parsing for weather |
| `date`   | GNU     | ✅ Yes   | Timezone-aware date display|

> **Note**: The script works without `python3`, but weather output will be limited to raw API response.

---

## Getting Started

### 1. Download the Script

```bash
git clone https://github.com/Lunatic16/cayman-weather.git
cd cayman-weather
```

### 2. Make It Executable

```bash
chmod +x cayman-weather.sh
```

### 3. Run It

```bash
./cayman-weather.sh
```

**Expected output:**

```
╔══════════════════════════════════════════╗
║  📍 Cayman Islands (George Town)
╠══════════════════════════════════════════╣
║  📅 Thursday, April 02, 2026
║  🕐 07:56:18 PM EST
╠══════════════════════════════════════════╣
║  🌤️  Current Weather:
║  Temperature: 26.1°C
║  Feels like:  28.1°C
║  Humidity:    80%
║  Wind:        21.4 km/h
║  Condition:   ☁️  Overcast
╚══════════════════════════════════════════╝
[INFO] Weather data retrieved successfully
```

---

## Usage

```bash
./cayman-weather.sh [OPTIONS]
```

### Options

| Flag               | Description                          |
|--------------------|--------------------------------------|
| `-h, --help`       | Show help message and exit           |
| `-v, --verbose`    | Enable debug output (API URL, raw JSON) |
| `-f, --fahrenheit` | Display temperature in Fahrenheit    |

### Examples

**Default (Celsius):**
```bash
./cayman-weather.sh
```

**Fahrenheit:**
```bash
./cayman-weather.sh --fahrenheit
```

**Debug mode:**
```bash
./cayman-weather.sh --verbose
```

**Help:**
```bash
./cayman-weather.sh --help
```

---

## Architecture

### Script Structure

```
cayman-weather.sh
├── Constants              # Location, API endpoint, colors
├── Logging Functions      # log_info, log_warn, log_error, log_debug
├── Usage & Help           # usage() - formatted help text
├── Dependency Check       # check_dependencies() - validates curl, python3
├── Cleanup Handler        # cleanup() - trap on EXIT
├── Argument Parsing       # parse_args() - handles flags
├── Display Functions      # print_header, print_datetime, print_weather_line
├── Weather Fetching       # fetch_weather_data() - curl to Open-Meteo
├── Weather Parsing        # parse_weather_data() - python3 JSON parser
└── Main Function          # main() - orchestrates all phases
```

### Execution Flow

```
1. parse_args()        → Process CLI flags
2. check_dependencies() → Verify curl, python3 available
3. print_header()      → Display location banner
4. print_datetime()    → Show Cayman Islands date/time
5. fetch_weather_data() → GET request to Open-Meteo API
6. parse_weather_data() → Extract fields from JSON response
7. print_weather_line() → Format and display each weather metric
8. cleanup()           → Exit handler (trap)
```

### Weather API Integration

**Endpoint:** `https://api.open-meteo.com/v1/forecast`

**Parameters:**
```
latitude=19.2866
longitude=-81.3744
current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m,wind_direction_10m
timezone=America/Cayman
temperature_unit=fahrenheit  # (optional, if --fahrenheit flag)
```

**Response fields parsed:**
- `temperature_2m` — Current temperature
- `apparent_temperature` — Feels-like temperature
- `relative_humidity_2m` — Humidity percentage
- `wind_speed_10m` — Wind speed
- `weather_code` — WMO weather condition code (0-99)

### WMO Weather Code Mapping

| Code | Condition                  | Code | Condition                    |
|------|----------------------------|------|------------------------------|
| 0    | ☀️ Clear sky               | 61   | 🌧️ Slight rain              |
| 1    | 🌤️ Mainly clear           | 63   | 🌧️ Moderate rain            |
| 2    | ⛅ Partly cloudy           | 65   | 🌧️ Heavy rain               |
| 3    | ☁️ Overcast                | 80   | 🌦️ Slight rain showers      |
| 45   | 🌫️ Foggy                  | 95   | ⛈️ Thunderstorm             |
| 51   | 🌦️ Light drizzle          | 96   | ⛈️ Thunderstorm with hail   |

---

## Exit Codes

| Code | Meaning                  | When It Occurs                        |
|------|--------------------------|---------------------------------------|
| 0    | Success                  | Weather data retrieved successfully   |
| 1    | General error            | Unknown flag, invalid arguments       |
| 2    | Missing dependency       | `curl` or `python3` not found         |
| 3    | Network/API failure      | Open-Meteo unreachable or timeout     |

---

## Environment Variables

The script does not require any environment variables. All configuration is hardcoded:

| Constant         | Value              | Purpose                    |
|------------------|--------------------|----------------------------|
| `LAT`            | `19.2866`          | Cayman Islands latitude    |
| `LON`            | `-81.3744`         | Cayman Islands longitude   |
| `LOCATION_TZ`    | `America/Cayman`   | Timezone (EST, UTC-5)      |
| `API_TIMEOUT`    | `10`               | Curl timeout in seconds    |

---

## Quality Assurance

### Shellcheck

The script passes Shellcheck with zero warnings:

```bash
shellcheck cayman-weather.sh
# (no output = clean)
```

### Defensive Patterns

- **`set -euo pipefail`** — Strict mode: exit on error, undefined vars, pipe failures
- **`readonly` constants** — Prevents accidental mutation of configuration values
- **Trap handler** — Cleanup function runs on EXIT for proper resource management
- **Dependency validation** — Checks for `curl` before attempting API calls
- **Graceful degradation** — Works without `python3` (limited output)
- **TTY detection** — Disables ANSI colors when output is piped to file/pipe

---

## Troubleshooting

### Weather shows "Unavailable"

**Cause:** Network issue or Open-Meteo API down

**Solution:**
```bash
# Test API connectivity
curl -s --max-time 10 "https://api.open-meteo.com/v1/forecast?latitude=19.2866&longitude=-81.3744&current=temperature_2m"

# Run with verbose logging
./cayman-weather.sh --verbose
```

### Colors not showing

**Cause:** Output is being piped or redirected

**Solution:** Colors are automatically disabled for non-TTY output. This is intentional for clean log files.

### Python3 parsing error

**Cause:** Malformed JSON response or python3 not installed

**Solution:**
```bash
# Verify python3 is available
command -v python3

# Check raw API response
./cayman-weather.sh --verbose 2>&1 | grep "Raw API"
```

### Wrong timezone

**Cause:** System doesn't have timezone data for `America/Cayman`

**Solution:**
```bash
# Verify timezone is available
timedatectl list-timezones | grep Cayman

# Install tzdata if missing (Ubuntu/Debian)
sudo apt-get install tzdata
```

---

## Customization

### Change Location

Edit the constants at the top of the script:

```bash
# Location (George Town, Cayman Islands)
readonly LAT="19.2866"
readonly LON="-81.3744"
readonly LOCATION_TZ="America/Cayman"
readonly LOCATION_NAME="Cayman Islands (George Town)"
```

### Add More Weather Metrics

Modify the API request in `fetch_weather_data()`:

```bash
# Add precipitation, UV index, pressure
&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m,wind_direction_10m,precipitation,uv,pressure_msl
```

Then update the Python parser in `parse_weather_data()` to extract and display the new fields.

### Change Output Format

Modify the `print_*` functions to customize the display format, or pipe to other tools:

```bash
# Save to file (colors auto-disabled)
./cayman-weather.sh > weather.txt

# Extract just temperature
./cayman-weather.sh --verbose 2>&1 | grep "Temperature"
```

---

## License

This script is provided as-is for personal and educational use. No warranty expressed or implied.

---

## Credits

- **Weather Data**: [Open-Meteo API](https://open-meteo.com/) — Free, open-source weather API
- **WMO Codes**: [World Meteorological Organization](https://www.wmo.int/) — Weather condition codes
- **Bash Best Practices**: [bash-defensive-patterns](https://github.com/bash-defensive-patterns) — Defensive scripting patterns
