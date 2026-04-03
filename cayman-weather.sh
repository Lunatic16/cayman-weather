#!/usr/bin/env bash
#
# cayman-weather.sh - Display current date/time and weather for Cayman Islands
#
# Usage: ./cayman-weather.sh [OPTIONS]
#
# Options:
#   -h, --help       Show this help message
#   -v, --verbose    Enable verbose output (debug mode)
#   -f, --fahrenheit Display temperature in Fahrenheit
#
# Dependencies: curl, python3 (for JSON parsing)
# Exit Codes:
#   0 - Success
#   1 - General error
#   2 - Missing dependency
#   3 - Network/API failure
#

set -euo pipefail

# ============================================================================
# Constants
# ============================================================================
readonly SCRIPT_VERSION="1.0.0"
SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_NAME

# Location (George Town, Cayman Islands)
readonly LAT="19.2866"
readonly LON="-81.3744"
readonly LOCATION_TZ="America/Cayman"
readonly LOCATION_NAME="Cayman Islands (George Town)"

# API endpoint
readonly WEATHER_API="https://api.open-meteo.com/v1/forecast"
readonly API_TIMEOUT=10

# ============================================================================
# Color Codes (with safe fallback for non-TTY)
# ============================================================================
if [[ -t 1 ]]; then
    readonly BOLD='\033[1m'
    readonly CYAN='\033[0;36m'
    readonly YELLOW='\033[1;33m'
    readonly GREEN='\033[0;32m'
    readonly MAGENTA='\033[0;35m'
    readonly RED='\033[0;31m'
    readonly RESET='\033[0m'
else
    readonly BOLD=''
    readonly CYAN=''
    readonly YELLOW=''
    readonly GREEN=''
    readonly MAGENTA=''
    readonly RED=''
    readonly RESET=''
fi

# ============================================================================
# Logging Functions
# ============================================================================
log_info() {
    echo -e "${GREEN}[INFO]${RESET} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${RESET} $*" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${RESET} $*" >&2
}

log_debug() {
    if [[ "${VERBOSE:-false}" == "true" ]]; then
        echo -e "${MAGENTA}[DEBUG]${RESET} $*" >&2
    fi
}

# ============================================================================
# Usage & Help
# ============================================================================
usage() {
    echo -e "${BOLD}${SCRIPT_NAME}${RESET} v${SCRIPT_VERSION}

Display current date/time and weather for Cayman Islands.

${BOLD}USAGE:${RESET}
    ${SCRIPT_NAME} [OPTIONS]

${BOLD}OPTIONS:${RESET}
    -h, --help       Show this help message and exit
    -v, --verbose    Enable verbose/debug output
    -f, --fahrenheit Display temperature in Fahrenheit

${BOLD}EXAMPLES:${RESET}
    ${SCRIPT_NAME}                    # Default (Celsius)
    ${SCRIPT_NAME} --fahrenheit       # Fahrenheit output
    ${SCRIPT_NAME} --verbose          # Debug mode

${BOLD}DEPENDENCIES:${RESET}
    curl, python3

${BOLD}EXIT CODES:${RESET}
    0  Success
    1  General error
    2  Missing dependency
    3  Network/API failure"
}

# ============================================================================
# Dependency Check
# ============================================================================
check_dependencies() {
    local missing=()

    if ! command -v curl &>/dev/null; then
        missing+=("curl")
    fi

    if [[ ${#missing[@]} -gt 0 ]]; then
        log_error "Missing required dependencies: ${missing[*]}"
        return 2
    fi

    # Python3 is optional (fallback without it)
    if ! command -v python3 &>/dev/null; then
        log_warn "python3 not found - weather parsing will be limited"
        return 0
    fi

    return 0
}

# ============================================================================
# Cleanup Handler
# ============================================================================
cleanup() {
    local exit_code=$?
    if [[ ${exit_code} -ne 0 ]]; then
        log_debug "Script exited with code: ${exit_code}"
    fi
    # Add any temp file cleanup here if needed
}
trap cleanup EXIT

# ============================================================================
# Argument Parsing
# ============================================================================
VERBOSE="false"
TEMP_UNIT="celsius"

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help)
                usage
                exit 0
                ;;
            -v|--verbose)
                VERBOSE="true"
                shift
                ;;
            -f|--fahrenheit)
                TEMP_UNIT="fahrenheit"
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
}

# ============================================================================
# Display Functions
# ============================================================================
print_header() {
    echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════╗${RESET}"
    echo -e "${BOLD}${CYAN}║${RESET}  ${YELLOW}📍 ${LOCATION_NAME}${RESET}"
    echo -e "${BOLD}${CYAN}╠══════════════════════════════════════════╣${RESET}"
}

print_datetime() {
    local date_str time_str
    date_str="$(TZ="${LOCATION_TZ}" date '+%A, %B %d, %Y')"
    time_str="$(TZ="${LOCATION_TZ}" date '+%I:%M:%S %p %Z')"

    echo -e "${BOLD}${CYAN}║${RESET}  📅 ${date_str}"
    echo -e "${BOLD}${CYAN}║${RESET}  🕐 ${time_str}"
    echo -e "${BOLD}${CYAN}╠══════════════════════════════════════════╣${RESET}"
}

print_weather_header() {
    echo -e "${BOLD}${CYAN}║${RESET}  🌤️  Current Weather:"
}

print_weather_line() {
    local line="$1"
    echo -e "${BOLD}${CYAN}║${RESET}  ${GREEN}${line}${RESET}"
}

print_footer() {
    echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════╝${RESET}"
}

# ============================================================================
# Weather Data Fetching
# ============================================================================
fetch_weather_data() {
    local temperature_param="temperature_2m"

    if [[ "${TEMP_UNIT}" == "fahrenheit" ]]; then
        temperature_param="temperature_2m"
    fi

    local url="${WEATHER_API}?latitude=${LAT}&longitude=${LON}&current=${temperature_param},relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m,wind_direction_10m&timezone=${LOCATION_TZ}"

    if [[ "${TEMP_UNIT}" == "fahrenheit" ]]; then
        url="${url}&temperature_unit=fahrenheit"
    fi

    log_debug "Fetching weather data from: ${url}"

    local response
    response="$(curl -s --max-time "${API_TIMEOUT}" "${url}" 2>/dev/null)" || {
        log_error "Failed to connect to weather API"
        return 3
    }

    if [[ -z "${response}" ]]; then
        log_error "Empty response from weather API"
        return 3
    fi

    log_debug "Raw API response: ${response}"
    echo "${response}"
}

# ============================================================================
# Weather Data Parsing
# ============================================================================
parse_weather_data() {
    local weather_json="$1"

    if ! command -v python3 &>/dev/null; then
        log_error "python3 required for weather parsing but not found"
        return 2
    fi

    python3 -c "
import json
import sys

try:
    data = json.loads(sys.argv[1])
except json.JSONDecodeError as e:
    print(f'Error parsing JSON: {e}', file=sys.stderr)
    sys.exit(1)

current = data.get('current', {})
units = data.get('current_units', {})

temp = current.get('temperature_2m', 'N/A')
temp_unit = units.get('temperature_2m', '°C')
feels_like = current.get('apparent_temperature', 'N/A')
humidity = current.get('relative_humidity_2m', 'N/A')
wind_speed = current.get('wind_speed_10m', 'N/A')
wind_unit = units.get('wind_speed_10m', 'km/h')
weather_code = current.get('weather_code', -1)

# WMO Weather code descriptions
weather_codes = {
    0: '☀️  Clear sky',
    1: '🌤️  Mainly clear',
    2: '⛅ Partly cloudy',
    3: '☁️  Overcast',
    45: '🌫️  Foggy',
    48: '🌫️  Depositing rime fog',
    51: '🌦️  Light drizzle',
    53: '🌦️  Moderate drizzle',
    55: '🌧️  Dense drizzle',
    61: '🌧️  Slight rain',
    63: '🌧️  Moderate rain',
    65: '🌧️  Heavy rain',
    71: '🌨️  Slight snow',
    73: '🌨️  Moderate snow',
    75: '❄️  Heavy snow',
    80: '🌦️  Slight rain showers',
    81: '🌧️  Moderate rain showers',
    82: '⛈️  Violent rain showers',
    95: '⛈️  Thunderstorm',
    96: '⛈️  Thunderstorm with hail',
    99: '⛈️  Thunderstorm with heavy hail'
}

weather_desc = weather_codes.get(weather_code, f'Unknown ({weather_code})')

print(f'Temperature: {temp}{temp_unit}')
print(f'Feels like:  {feels_like}{temp_unit}')
print(f'Humidity:    {humidity}%')
print(f'Wind:        {wind_speed} {wind_unit}')
print(f'Condition:   {weather_desc}')
" "${weather_json}"
}

# ============================================================================
# Main Function
# ============================================================================
main() {
    parse_args "$@"
    check_dependencies || exit $?

    # Display header and datetime
    print_header
    print_datetime

    # Fetch and display weather
    print_weather_header

    local weather_json
    weather_json="$(fetch_weather_data)" || exit $?

    local weather_output
    weather_output="$(parse_weather_data "${weather_json}" 2>/dev/null)" || {
        log_warn "Failed to parse weather data"
        print_weather_line "Weather data unavailable"
        print_footer
        return 0
    }

    if [[ -n "${weather_output}" ]]; then
        while IFS= read -r line; do
            print_weather_line "${line}"
        done <<< "${weather_output}"
    else
        print_weather_line "No weather data available"
    fi

    print_footer

    log_info "Weather data retrieved successfully"
    return 0
}

# ============================================================================
# Entry Point
# ============================================================================
main "$@"
