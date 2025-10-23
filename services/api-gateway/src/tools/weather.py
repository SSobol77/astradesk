# SPDX-License-Identifier: Apache-2.0
# services/api-gateway/src/tools/weather.py
"""Narzędzie do pobierania aktualnych danych pogodowych z zewnętrznego API.

Moduł ten dostarcza w pełni funkcjonalną, gotową na produkcję integrację
z serwisem pogodowym OpenWeatherMap. Jest przykładem profesjonalnego
podejścia do interakcji z zewnętrznymi, publicznymi API.

Główne cechy:
- **Rzeczywista Integracja**: Wykonuje asynchroniczne zapytania HTTP do
  API OpenWeatherMap, aby pobrać aktualne warunki pogodowe.
- **Bezpieczne Zarządzanie Kluczem API**: Klucz API jest ładowany w bezpieczny
  sposób ze zmiennych środowiskowych i nigdy nie jest hardkodowany w kodzie.
- **Cache'owanie Wyników**: Wykorzystuje prosty, wbudowany w pamięć cache z TTL
  (Time-To-Live), aby unikać wielokrotnego odpytywania API o te same dane
  w krótkim czasie. Zmniejsza to koszty i zużycie limitów API.
- **Solidna Obsługa Błędów**: Przechwytuje i interpretuje kody statusu HTTP
  zwracane przez API, dostarczając użytkownikowi czytelnych komunikatów
  o błędach (np. miasto nie znalezione, nieprawidłowy klucz API).
- **Walidacja Wejścia**: Sprawdza, czy podane jednostki są obsługiwane.

Wymagana konfiguracja:
- Zmienna środowiskowa `WEATHER_API_KEY` musi zawierać ważny klucz API
  z serwisu OpenWeatherMap.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, Dict, Final, Literal, Tuple

import httpx

logger = logging.getLogger(__name__)

# --- Konfiguracja ---

# Klucz API ładowany ze zmiennych środowiskowych.
WEATHER_API_KEY: Final[str] = os.getenv("WEATHER_API_KEY", "")
OPENWEATHER_API_URL: Final[str] = "https://api.openweathermap.org/data/2.5/weather"

# Czas życia cache'a w sekundach. Pogoda nie zmienia się co chwilę.
CACHE_TTL_SECONDS: Final[int] = 600  # 10 minut

# Typ dla jednostek, aby zapewnić poprawność i ułatwić walidację.
Unit = Literal["metric", "imperial", "standard"]

# --- Prosty, wbudowany cache w pamięci ---
_cache: Dict[Tuple[str, Unit], Tuple[float, Dict[str, Any]]] = {}
_cache_lock = asyncio.Lock()


class WeatherAPIError(Exception):
    """Wyjątek bazowy dla błędów związanych z API pogodowym."""
    pass


async def get_weather(city: str, unit: str = "metric") -> str:
    """Pobiera aktualne warunki pogodowe dla podanego miasta.

    Funkcja najpierw sprawdza wewnętrzny cache. Jeśli dane są aktualne,
    zwraca je natychmiast. W przeciwnym razie, odpytuje API OpenWeatherMap,
    aktualizuje cache i zwraca świeże dane.

    Args:
        city: Nazwa miasta (np. "Warsaw", "New York").
        unit: System jednostek. Dozwolone wartości: 'metric' (Celsjusz),
              'imperial' (Fahrenheit), 'standard' (Kelwin). Domyślnie 'metric'.

    Returns:
        Sformatowany string z warunkami pogodowymi lub komunikat o błędzie.
    """
    if not WEATHER_API_KEY:
        logger.error("Klucz API dla serwisu pogodowego (WEATHER_API_KEY) nie jest skonfigurowany.")
        return "Błąd: Usługa pogodowa jest nieskonfigurowana. Skontaktuj się z administratorem."

    # --- Krok 1: Walidacja wejścia ---
    normalized_unit = unit.lower()
    if normalized_unit not in ("metric", "imperial", "standard"):
        return f"Błąd: Nieprawidłowa jednostka '{unit}'. Dostępne opcje: 'metric', 'imperial', 'standard'."

    # --- Krok 2: Sprawdzenie cache'a ---
    cache_key = (city.lower(), normalized_unit)
    now = time.time()
    async with _cache_lock:
        if cache_key in _cache:
            timestamp, data = _cache[cache_key]
            if now - timestamp < CACHE_TTL_SECONDS:
                logger.info(f"Zwracanie danych pogodowych dla '{city}' z cache'a.")
                return _format_weather_data(data, normalized_unit)

    # --- Krok 3: Wywołanie API (jeśli brak w cache'u) ---
    logger.info(f"Pobieranie świeżych danych pogodowych dla '{city}' z API.")
    params = {
        "q": city,
        "appid": WEATHER_API_KEY,
        "units": normalized_unit,
        "lang": "pl", # Można sparametryzować
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(OPENWEATHER_API_URL, params=params)
            response.raise_for_status()
            
            api_data = response.json()
            
            # --- Krok 4: Aktualizacja cache'a ---
            async with _cache_lock:
                _cache[cache_key] = (time.time(), api_data)
                
            return _format_weather_data(api_data, normalized_unit)

    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        if status == 401:
            logger.error("Błąd autoryzacji w API pogodowym: nieprawidłowy klucz API.")
            return "Błąd: Wystąpił problem z autoryzacją w serwisie pogodowym."
        elif status == 404:
            logger.warning(f"Nie znaleziono miasta '{city}' w serwisie pogodowym.")
            return f"Błąd: Nie udało się znaleźć miasta o nazwie '{city}'."
        elif status == 429:
            logger.warning("Przekroczono limit zapytań do API pogodowego.")
            return "Błąd: Usługa pogodowa jest tymczasowo przeciążona. Spróbuj ponownie za chwilę."
        else:
            logger.error(f"Błąd HTTP {status} podczas zapytania do API pogodowego: {e.response.text}")
            return f"Błąd: Serwis pogodowy zwrócił nieoczekiwany błąd (status: {status})."
    except (httpx.RequestError, asyncio.TimeoutError) as e:
        logger.error(f"Błąd sieciowy podczas komunikacji z API pogodowym: {e}")
        return "Błąd: Nie można połączyć się z serwisem pogodowym."
    except Exception as e:
        logger.critical(f"Nieoczekiwany błąd w narzędziu pogodowym dla '{city}': {e}", exc_info=True)
        return "Błąd: Wystąpił krytyczny błąd wewnętrzny w usłudze pogodowej."


def _format_weather_data(data: Dict[str, Any], unit: Unit) -> str:
    """Formatuje dane JSON z API w czytelny dla człowieka string."""
    try:
        city_name = data["name"]
        description = data["weather"][0]["description"]
        temp = data["main"]["temp"]
        humidity = data["main"]["humidity"]
        wind_speed = data["wind"]["speed"]

        unit_symbols = {
            "metric": ("°C", "m/s"),
            "imperial": ("°F", "mph"),
            "standard": ("K", "m/s"),
        }
        temp_symbol, speed_symbol = unit_symbols[unit]

        return (
            f"Pogoda dla {city_name}: {description.capitalize()}.\n"
            f"- Temperatura: {temp:.1f} {temp_symbol}\n"
            f"- Wilgotność: {humidity}%\n"
            f"- Prędkość wiatru: {wind_speed} {speed_symbol}"
        )
    except (KeyError, IndexError):
        logger.error(f"Otrzymano nieprawidłowy format danych z API pogodowego: {data}")
        return "Błąd: Otrzymano niekompletne dane z serwisu pogodowego."
