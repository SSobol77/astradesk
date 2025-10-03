from __future__ import annotations
from typing import List, Dict, Any
from pydantic import BaseModel, ValidationError

BLOCKLIST = {"drop database", "rm -rf", "shutdown", "format c:", "disable security"}

def profanity_filter(text: str) -> bool:
    lowered = text.lower()
    return any(b in lowered for b in BLOCKLIST)

class PlanStepModel(BaseModel):
    name: str
    args: Dict[str, Any]

class PlanModel(BaseModel):
    steps: List[PlanStepModel]

def validate_plan_json(s: str) -> PlanModel:
    # Wymusza poprawny JSON i kształt planu
    try:
        import json
        data = json.loads(s)
        return PlanModel(**data)
    except (ValueError, ValidationError) as e:
        raise ValueError(f"Invalid plan JSON: {e}")

def clip_output(s: str, max_chars: int = 2000) -> str:
    return s if len(s) <= max_chars else s[:max_chars] + "…"
