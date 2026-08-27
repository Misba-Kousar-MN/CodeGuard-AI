import os
from typing import Optional

def compute_average(numbers: list[float]) -> Optional[float]:
    """Computes average safely checking for empty lists."""
    if not numbers:
        return None
    return sum(numbers) / len(numbers)

def fetch_environment_key() -> str:
    """Safely retrieves API key from environment."""
    return os.getenv("API_KEY", "")
