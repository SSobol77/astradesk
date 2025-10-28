# SPDX-License-Identifier: Apache-2.0
"""File: services/api-gateway/src/tools/weather.py

Project: AstraDesk Framework
Package:  AstraDesk API Gateway

Description:
    Asynchronous tool for fetching current weather from OpenWeatherMap.
    Integrates async HTTP, in-memory cache with TTL, OPA governance, 
    OpenTelemetry tracing, and RFC 7807 error handling.
    Production-ready with comprehensive error handling and caching.

Env:
    - WEATHER_API_KEY
    - OPENWEATHER_API_UR
    - CACHE_TTL_SECONDS

Author: Siergej Sobolewski
Since: 2025-10-25

"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, Dict, Final, Literal, Tuple, Optional

import httpx
from opentelemetry import trace
from opa_python_client import OPAClient

from model_gateway.base import ProblemDetail

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# Configuration
WEATHER_API_KEY: Final[str] = os.getenv("WEATHER_API_KEY", "")
OPENWEATHER_API_URL: Final[str] = "https://api.openweathermap.org/data/2.5/weather"
CACHE_TTL_SECONDS: Final[int] = 600  # 10 minutes
Unit = Literal["metric", "imperial", "standard"]

# In-memory cache
_cache: Dict[Tuple[str, Unit], Tuple[float, Dict[str, Any]]] = {}
_cache_lock = asyncio.Lock()


def redact_city_name(city: str) -> str:
    """Redacts city name for logging."""
    return city.lower() if len(city) <= 50 else "[REDACTED]"


class WeatherError(Exception):
    """Base error for weather tool."""
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def to_problem_detail(self) -> ProblemDetail:
        return ProblemDetail(
            type="https://astradesk.com/errors/weather",
            title="Weather API Error",
            detail=self.message,
            status=500
        )


async def get_weather(
    city: str,
    unit: str = "metric",
    opa_client: Optional[OPAClient] = None,
) -> str:
    """Fetches current weather for a city with cache, governance, and observability."""
    with tracer.start_as_current_span("tool.weather.get_weather") as span:
        span.set_attribute("city", redact_city_name(city))
        span.set_attribute("unit", unit)

        if not WEATHER_API_KEY:
            logger.error("WEATHER_API_KEY not configured")
            raise WeatherError("Weather service not configured")

        normalized_unit = unit.lower()
        if normalized_unit not in ("metric", "imperial", "standard"):
            error_msg = f"Invalid unit '{unit}'. Use 'metric', 'imperial', 'standard'."
            logger.warning(error_msg)
            raise WeatherError(error_msg)

        if opa_client:
            decision = await opa_client.check_policy(
                input={"city": city, "action": "weather"},
                policy_path="astradesk/tools/weather"
            )
            if not decision.get("result", True):
                logger.warning(f"OPA denied weather for {city}")
                raise WeatherError("Access denied by policy")

        cache_key = (city.lower(), normalized_unit)
        now = time.time()

        async with _cache_lock:
            if cache_key in _cache:
                timestamp, data = _cache[cache_key]
                if now - timestamp < CACHE_TTL_SECONDS:
                    logger.info(f"Cache hit for '{city}'")
                    span.add_event("cache_hit")
                    return _format_weather_data(data, normalized_unit)

        logger.info(f"Fetching weather for '{city}' from API")
        params = {
            "q": city,
            "appid": WEATHER_API_KEY,
            "units": normalized_unit,
            "lang": "en",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                with tracer.start_as_current_span("weather.api_call"):
                    response = await client.get(OPENWEATHER_API_URL, params=params)
                    response.raise_for_status()
                    api_data = response.json()

            async with _cache_lock:
                _cache[cache_key] = (time.time(), api_data)

            return _format_weather_data(api_data, normalized_unit)

        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status == 401:
                logger.error("Invalid WEATHER_API_KEY")
                raise WeatherError("Weather API authentication failed")
            elif status == 404:
                logger.warning(f"City not found: {city}")
                return f"Error: City '{city}' not found."
            elif status == 429:
                logger.warning("Rate limited by OpenWeatherMap")
                raise WeatherError("Weather service temporarily overloaded")
            else:
                logger.error(f"HTTP {status} from weather API: {e.response.text}")
                raise WeatherError(f"Weather service error (status {status})")
        except (httpx.RequestError, asyncio.TimeoutError) as e:
            logger.error(f"Network error: {e}")
            raise WeatherError("Cannot connect to weather service")
        except Exception as e:
            logger.critical(f"Unexpected error: {e}", exc_info=True)
            raise WeatherError("Internal error in weather tool")


def _format_weather_data(data: Dict[str, Any], unit: Unit) -> str:
    """Formats weather API response into human-readable string."""
    try:
        city_name = data["name"]
        description = data["weather"][0]["description"]
        temp = data["main"]["temp"]
        humidity = data["main"]["humidity"]
        wind_speed = data["wind"].get("speed", 0)

        unit_symbols = {
            "metric": ("°C", "m/s"),
            "imperial": ("°F", "mph"),
            "standard": ("K", "m/s"),
        }
        temp_symbol, speed_symbol = unit_symbols[unit]

        return (
            f"Weather in {city_name}: {description.capitalize()}.\n"
            f"- Temperature: {temp:.1f} {temp_symbol}\n"
            f"- Humidity: {humidity}%\n"
            f"- Wind speed: {wind_speed} {speed_symbol}"
        )
    except (KeyError, IndexError) as e:
        logger.error(f"Invalid weather data format: {e}")
        return "Error: Incomplete data from weather service."
