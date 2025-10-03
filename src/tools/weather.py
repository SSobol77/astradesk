# src/tools/weather.py

# A simple weather tool for demonstration purposes.
# In production, this would call a weather provider API.
# pylint: disable=unused-arguments   

from __future__ import annotations
from typing import Any

async def get_weather(city: str, unit: str = "C") -> str:
    # TODO: w produkcji wywołanie providera
    return f"{city}: 18°{unit}, clear"
