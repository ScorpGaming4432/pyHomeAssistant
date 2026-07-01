import inspect
from json import JSONDecodeError
import os
import sys
from collections.abc import Sequence
from collections import Counter
from typing import Any, Callable, Hashable, Literal, Mapping, TypeAlias, TypedDict, Union, Iterable
import time
import math
import random
import requests
import requests._types as req_T
from datetime import datetime
from html.parser import HTMLParser


from ollama._types import Tool

ToolsSequence: TypeAlias = Sequence[Union[Mapping[str, Any], Tool, Callable[..., Any]]]


class UrlFetchResult(TypedDict):
    """Structured result returned by get_url."""

    response: requests.Response
    content: Any


def _collect_available_functions() -> dict[str, Callable[..., Any]]:
    module = sys.modules[__name__]
    functions: dict[str, Callable] = {}

    for name, value in vars(module).items():
        if not inspect.isfunction(value):
            continue
        if value.__module__ != __name__:
            continue
        if name.startswith("_"):
            continue

        functions[name] = value

    # return sorted(functions, key=lambda fn: fn.__name__)
    return functions

# --------------------------------------------------
# Constants
# --------------------------------------------------
"""
Common mathematical constants and utility functions.
"""
PI = math.pi
E = math.e
TAU = math.tau
PHI = (1 + (math.sqrt(5))) / 2  # golden ratio
R = 8.31446261815324      # universal gas constant


# --------------------------------------------------
# Number theory
# --------------------------------------------------

def is_prime(n: int) -> bool:
    """Return True if n is a prime number.

    Args:
        n (int): Number to check if it is prime

    Returns:
        bool: True if prime. False if composite.
    """    

    if n < 2:
        return False
    if n in (2, 3):
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False

    i = 5
    w = 2
    limit = math.isqrt(n)

    while i <= limit:
        if n % i == 0:
            return False
        i += w
        w = 6 - w

    return True


def sum_digits(number: int | str | float) -> int:
    """Sums all digits from a number.
    Examples:
        number = 169\n
        1 + 6 + 9 = 16\n
        returns 16
        
        number = 3.141592653589793\n
        3 + 1 + 4 + 1 + 5 + 9 ...\n
        returns 88
        
        

    Args:
        number (int | str | float): A number interpretable as str to sum all digits of.

    Returns:
        int: Sum of provided number's digits
    """
    return sum(int(d) for d in str(number) if d.isdigit())


def gcd(a: int, b: int) -> int:
    """Greatest common divisor of two integers. Wrapper of `math.gcd()` to limit arguments used to only 2.

    Args:
        a (int): First integer
        b (int): Second integer

    Returns:
        int: Largest positive integer that divides each of the integers.
    """    
    return math.gcd(a, b)


def lcm(a: int, b: int) -> int:
    """Least common multiple of two integers.\n
    
    Since division of integers by zero is undefined, definition has meaning only if a and b are both different from zero. However, lcm(a, 0) is defined as 0 for all a, since 0 is the only common multiple of a and 0. 
    If both a and b are 0, the result would cause division by zero.

    Args:
        a (int): First integer
        b (int): Second integer

    Returns:
        int: Smallest positive integer that is divisible by both a and b
    """    
    return abs(a * b) // math.gcd(a, b)


def factorial(n: int) -> int:
    """Factorial of a number. Wrapper to math.factorial(n).

    Args:
        n (int): Non-negative integer

    Returns:
        int: Product of all positive integers less than or equal to n
    """    
    return math.factorial(n)


# --------------------------------------------------
# Geometry
# --------------------------------------------------

def is_triangle(a: float, b: float, c: float) -> bool:
    """Check if numbers interpreted as connected side lengths, could form a triangle.

    Args:
        a (float): First side length
        b (float): Second side length
        c (float): Third side length

    Returns:
        bool: True if side lengths could form any triangle.
    """    

    a, b, c = sorted(map(abs, (a, b, c)))
    return a + b > c


def is_right_triangle(a: float, b: float, c: float) -> bool:
    """Check if numbers interpreted as connected side lengths, could form a triangle. Since `float`s are passed, false-positives may happen. 

    Args:
        a (float): First side length
        b (float): Second side length
        c (float): Third side length

    Returns:
        bool: True if sides could form a right triangle
    """    

    a, b, c = sorted(map(abs, (a, b, c)))
    return math.isclose(a*a + b*b, c*c)

# --------------------------------------------------
# Randoms
# --------------------------------------------------

def get_random_integer_from_range(a:int, b:int) -> int:
    """Returns a random integer from range [a,b], that is, including both end points. Wrapper to random.randint(a, b)."""
    return random.randint(a,b)


# --------------------------------------------------
# Statistics / collections
# --------------------------------------------------

def count_occurrences(
    iterable: Iterable[Hashable],
    sort: Literal['asc', 'desc'] | None = None
) -> dict | list:
    """
    Count occurrences of elements in an iterable.

    Args:
        iterable: Input iterable
        sort: Sorting convention. 'asc' or 'desc'

    Returns:
        dict[element, count] if unsorted
        list[element] sorted by frequency otherwise
    """

    counts = Counter(iterable)

    if sort is None:
        return dict(counts)

    reverse = sort == "desc"
    return sorted(counts, key=counts.get, reverse=reverse)


# --------------------------------------------------
# Utilities
# --------------------------------------------------

def clamp(x: float, minimum: float, maximum: float) -> float:
    """Clamp value between minimum and maximum."""
    return max(minimum, min(x, maximum))


def sign(x: float) -> int:
    """Return the sign of x (-1, 0, 1)."""
    return (x > 0) - (x < 0)


def format_2d_array(array: list[list[Any]]) -> str:
    """Return a nicely aligned string representation of a 2D array."""

    max_len = max(len(str(x)) for row in array for x in row)

    lines = []
    for row in array:
        lines.append(" ".join(str(x).rjust(max_len) for x in row))

    return "\n".join(lines)

# --------------------------------------------------
# Internet functions
# --------------------------------------------------

def get_url(
    url: str,
    parameters: dict[str, str] | None = None,
    **kwargs: Any,
) -> UrlFetchResult:
    """Fetch a URL and return both the HTTP response and parsed content.

    The function attempts to parse the response body as JSON. When that fails,
    it falls back to the raw response bytes so callers can still inspect the
    body without raising an exception.

    Args:
        url: The URL to request.
        parameters: Optional query parameters forwarded to requests.get.
        **kwargs: Additional keyword arguments forwarded to requests.get.

    Returns:
        A dictionary-like result with two fields:
        - response: the completed requests.Response object
        - content: parsed JSON data when available, otherwise raw bytes
    """
    request: requests.Response = requests.get(url, params=parameters, **kwargs)
    try:
        result = request.json()
    except (JSONDecodeError, ValueError) as exc:
        print("Attempting to read the result. (JSON FAILED)", exc)
        result = request.content

    return {"response": request, "content": result}
    

def get_current_server_time():
    return time.ctime(time.time())

def get_time_by_IANA(area: str, location: str) -> str:
    """Fetches the current time for a specified IANA time zone.

    Args:
        area (str): The geographical area (e.g., "America", "Europe").
        location (str): The specific location within the area (e.g., "New_York", "London").

    Returns:
        str: The current time in ISO format for the specified time zone.
    """
    url = f"http://worldtimeapi.org/api/timezone/{area}/{location}"
    result = get_url(url)
    if result['response'].status_code == 200 and isinstance(result['content'], dict):
        return result['content']['datetime']
    return f"Error: Could not retrieve time for {area}/{location}"


def _convert_to_datetime_object(dt_object: str | datetime) -> datetime:
    """Converts a string or datetime object to a datetime object.

    Args:
        dt_object (str | datetime): The datetime object or string to convert.

    Returns:
        datetime: The converted datetime object.
    """
    if isinstance(dt_object, str):
        return datetime.fromisoformat(dt_object)
    return dt_object


def get_date(dt_object: str | datetime = None) -> str:
    """Returns the current date in YYYY-MM-DD format, or the date of a provided datetime object.

    Args:
        dt_object (str | datetime, optional): A datetime object or string to extract the date from. Defaults to None, which means the current date.

    Returns:
        str: The date in 'YYYY-MM-DD' format.
    """
    if dt_object is None:
        return datetime.now().strftime('%Y-%m-%d')
    return _convert_to_datetime_object(dt_object).strftime('%Y-%m-%d')


def get_date_time(dt_object: str | datetime = None) -> str:
    """Returns the current date and time in ISO format, or the date and time of a provided datetime object.

    Args:
        dt_object (str | datetime, optional): A datetime object or string to format. Defaults to None, which means the current date and time.

    Returns:
        str: The date and time in ISO format (YYYY-MM-DDTHH:MM:SS.ffffff).
    """
    if dt_object is None:
        return datetime.now().isoformat()
    return _convert_to_datetime_object(dt_object).isoformat()

class _HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.recording = True
        self.text_parts = []
        self.ignored_tags = {"script", "style", "head", "meta", "link", "noscript", "svg"}

    def handle_starttag(self, tag, attrs):
        if tag in self.ignored_tags:
            self.recording = False

    def handle_endtag(self, tag):
        if tag in self.ignored_tags:
            self.recording = True

    def handle_data(self, data):
        if self.recording:
            cleaned = data.strip()
            if cleaned:
                self.text_parts.append(cleaned)

    def get_text(self) -> str:
        return "\n".join(self.text_parts)


def get_webpage_text(url: str) -> str:
    """Fetch a webpage and extract its readable plain text, removing HTML tags, scripts, and styling.

    Args:
        url (str): The URL of the webpage to fetch and parse.

    Returns:
        str: The plain text content of the webpage, or an error message.
    """
    print(f'Reading web as text: {url} ...')
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        if response.status_code != 200:
            return f"Error: Received HTTP status code {response.status_code}."
        
        # Check if content type is HTML
        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
            # For JSON, XML, or plain text, just return response text or snippet
            return response.text[:10000]

        parser = _HTMLTextExtractor()
        parser.feed(response.text)
        extracted_text = parser.get_text()
        
        # Clean up excess whitespace and limit size to avoid token overflow
        lines = [line.strip() for line in extracted_text.splitlines() if line.strip()]
        cleaned_text = "\n".join(lines)
        return cleaned_text[:10000]  # Limit to 10k chars to protect context window
    except Exception as e:
        return f"Error fetching webpage: {e}"


# --------------------------------------------------
# Home Assistant functions
# --------------------------------------------------

def hass_get_state(entity_id: str) -> dict | str:
    """Retrieve the current state and attributes of a specific Home Assistant entity.

    Args:
        entity_id (str): The entity ID (e.g., 'light.living_room', 'sensor.temperature').

    Returns:
        dict | str: The state object if successful, or an error message.
    """
    url = os.environ.get("HASS_URL", "http://localhost:8123")
    token = os.environ.get("HASS_TOKEN") or os.environ.get("SUPERVISOR_TOKEN")
    
    if not token:
        return "Error: Home Assistant token is not configured. Please set the HASS_TOKEN environment variable."
        
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    
    try:
        response = requests.get(f"{url.rstrip('/')}/api/states/{entity_id}", headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return f"Error: Entity {entity_id} not found."
        else:
            return f"Error: Failed to fetch state. HTTP status {response.status_code}."
    except Exception as e:
        return f"Error connecting to Home Assistant: {e}"


def hass_list_states() -> list | str:
    """Retrieve the current states and attributes of all entities in Home Assistant.

    Returns:
        list | str: A list of state objects if successful, or an error message.
    """
    url = os.environ.get("HASS_URL", "http://localhost:8123")
    token = os.environ.get("HASS_TOKEN") or os.environ.get("SUPERVISOR_TOKEN")
    
    if not token:
        return "Error: Home Assistant token is not configured. Please set the HASS_TOKEN environment variable."
        
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    
    try:
        response = requests.get(f"{url.rstrip('/')}/api/states", headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return f"Error: Failed to fetch states. HTTP status {response.status_code}."
    except Exception as e:
        return f"Error connecting to Home Assistant: {e}"


def hass_call_service(domain: str, service: str, service_data: dict[str, Any] | None = None) -> list | str:
    """Call a service in Home Assistant to control devices.

    Args:
        domain (str): The domain of the service (e.g., 'light', 'switch', 'climate', 'media_player').
        service (str): The service name (e.g., 'turn_on', 'turn_off', 'set_temperature', 'volume_mute').
        service_data (dict, optional): Dict of arguments for the service (e.g., {"entity_id": "light.living_room", "brightness": 150}).

    Returns:
        list | str: List of states that changed as a result of the service call, or an error message.
    """
    url = os.environ.get("HASS_URL", "http://localhost:8123")
    token = os.environ.get("HASS_TOKEN") or os.environ.get("SUPERVISOR_TOKEN")
    
    if not token:
        return "Error: Home Assistant token is not configured. Please set the HASS_TOKEN environment variable."
        
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    
    if service_data is None:
        service_data = {}
        
    try:
        response = requests.post(
            f"{url.rstrip('/')}/api/services/{domain}/{service}",
            headers=headers,
            json=service_data,
            timeout=15
        )
        if response.status_code in (200, 201):
            return response.json()
        else:
            return f"Error: Failed to call service. HTTP status {response.status_code}. Response: {response.text}"
    except Exception as e:
        return f"Error connecting to Home Assistant: {e}"


# --------------------------------------------------
# Live Data API functions
# --------------------------------------------------

def get_weather_forecast(latitude: float, longitude: float) -> dict | str:
    """Fetch current weather and a 7-day forecast for a given latitude and longitude using Open-Meteo.

    Args:
        latitude (float): Latitude of the location.
        longitude (float): Longitude of the location.

    Returns:
        dict | str: Detailed weather forecast data or an error message.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current_weather": "true",
        "daily": "temperature_2m_max,temperature_2m_max,precipitation_probability_max,weathercode",
        "timezone": "auto"
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return f"Error: Open-Meteo API returned status {response.status_code}."
    except Exception as e:
        return f"Error fetching weather forecast: {e}"


def get_sunrise_sunset(latitude: float, longitude: float) -> dict | str:
    """Fetch sunrise, sunset, and solar details for a location based on coordinates using Sunrise-Sunset.org.

    Args:
        latitude (float): Latitude of the location.
        longitude (float): Longitude of the location.

    Returns:
        dict | str: Sunrise/sunset times (UTC) and day length, or an error message.
    """
    url = "https://api.sunrise-sunset.org/json"
    params = {
        "lat": latitude,
        "lng": longitude,
        "formatted": 0  # Get ISO 8601 formatted times
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "OK":
                return data.get("results", {})
            return f"Error from sunrise-sunset API: {data.get('status')}"
        else:
            return f"Error: Sunrise-Sunset API returned status {response.status_code}."
    except Exception as e:
        return f"Error fetching sunrise/sunset: {e}"


def get_location_by_ip() -> dict | str:
    """Detect location coordinates and timezone based on the current external IP address using ip-api.com.

    Returns:
        dict | str: Location details (lat, lon, timezone, city, country, ip) or an error message.
    """
    url = "http://ip-api.com/json/"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                return {
                    "latitude": data.get("lat"),
                    "longitude": data.get("lon"),
                    "timezone": data.get("timezone"),
                    "city": data.get("city"),
                    "country": data.get("country"),
                    "query_ip": data.get("query")
                }
            return f"Error: IP Geolocation failed with status {data.get('message')}."
        else:
            return f"Error: IP Geolocation API returned status {response.status_code}."
    except Exception as e:
        return f"Error fetching geolocation: {e}"


def get_public_holidays(country_code: str, year: int | None = None) -> list | str:
    """Fetch public holidays for a given country code and year using Nager.Date.

    Args:
        country_code (str): Two-letter ISO country code (e.g., 'US', 'PL', 'GB').
        year (int, optional): The year to fetch holidays for. Defaults to the current year.

    Returns:
        list | str: List of holidays or an error message.
    """
    if year is None:
        year = datetime.now().year
    
    url = f"https://date.nager.at/api/v3/PublicHolidays/{year}/{country_code}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return f"Error: Country code '{country_code}' or year '{year}' not supported."
        else:
            return f"Error: Nager.Date API returned status {response.status_code}."
    except Exception as e:
        return f"Error fetching public holidays: {e}"


AVAILABLE_FUNCTIONS: dict[str, Callable[..., Any]] = _collect_available_functions()


# --------------------------------------------------
# Public API
# --------------------------------------------------

__all__: list[str] = [
    "PI", "E", "TAU", "PHI", "R",

    "is_prime",
    "sum_digits",
    "gcd",
    "lcm",
    "factorial",

    "is_triangle",
    "is_right_triangle",

    "count_occurrences",

    "clamp",
    "sign",
    "format_2d_array",
    "get_date",
    "get_date_time",

    "get_url",
    "get_current_server_time",
    "get_time_by_IANA",
    "get_webpage_text",
    "hass_get_state",
    "hass_list_states",
    "hass_call_service",
    "get_weather_forecast",
    "get_sunrise_sunset",
    "get_location_by_ip",
    "get_public_holidays",
]
# print(AVAILABLE_FUNCTIONS)