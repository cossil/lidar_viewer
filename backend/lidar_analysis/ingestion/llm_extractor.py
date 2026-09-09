"""OpenRouter LLM-assisted datasheet extractor (PRD §11-12, Decision D025).

Uses OpenRouter API (model: z-ai/glm-5.3-flash) to extract structured LiDAR technical specifications
from unstructured datasheet text while preserving provenance and avoiding hallucinated specs (Rule 1).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
import urllib.request


def get_openrouter_api_key() -> Optional[str]:
    """Resolve OpenRouter API key from environment variable or local config."""
    key = os.environ.get("OPENROUTER_API_KEY")
    if key and key.strip():
        return key.strip()

    # Fallback to hermes .env or workspace .env
    repo_root = Path(__file__).resolve().parents[3]
    candidate_files = [
        repo_root / ".env",
        Path(r"C:\Users\cossi\AppData\Local\hermes\.env"),
        Path(".env"),
        Path("../.env"),
    ]
    for p in candidate_files:
        if p.exists():
            try:
                for line in p.read_text(encoding="utf-8").splitlines():
                    if line.startswith("OPENROUTER_API_KEY="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val:
                            return val
            except Exception:
                continue
    return None


SYSTEM_PROMPT = """You are an expert LiDAR hardware specifications parser for the SilvaLab LiDAR Analysis Platform.
Your task is to extract exact technical specifications from the provided datasheet text into a structured JSON object.

RULES:
1. NEVER invent, guess, or fabricate specifications (Rule 1). If a parameter is not explicitly stated, omit it or set it to null.
2. Maintain SI units or provide the original unit explicitly.
3. Return ONLY valid JSON matching this schema:
{
  "sensor_id": string (e.g. "hesai-qt64"),
  "manufacturer": string,
  "model": string,
  "version": string (default "1.0.0" if unstated),
  "sensor_type": string (one of: "mechanical_spinning", "solid_state", "mems", "optical_phased_array"),
  "range": {
    "maximum": {"value": number, "unit": "m"},
    "minimum": {"value": number, "unit": "m"}
  },
  "accuracy": {
    "range": {"value": number, "unit": "m"}
  },
  "beam": {
    "horizontal_divergence": {"value": number, "unit": "rad"},
    "vertical_divergence": {"value": number, "unit": "rad"},
    "beam_shape": "circular" | "elliptical"
  },
  "scan": {
    "point_rate": {"value": number, "unit": "Hz"},
    "rotation_frequency": {"value": number, "unit": "Hz"},
    "frame_rate": {"value": number, "unit": "Hz"}
  },
  "extracted_notes": string
}
"""


def _parse_json_content(content_str: str) -> Dict[str, Any]:
    cleaned = (content_str or "").strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return json.loads(cleaned)


def extract_with_openrouter(
    raw_text: str,
    model: str = "z-ai/glm-5.3-flash",
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Extract LiDAR specs using OpenRouter API."""
    key = api_key or get_openrouter_api_key()
    if not key:
        raise ValueError("OPENROUTER_API_KEY not found in environment or configuration.")

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Extract technical specifications from this LiDAR datasheet text:\n\n{raw_text[:8000]}",
            },
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.0,
    }

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://127.0.0.1:8000",
        "X-Title": "SilvaLab LiDAR Analysis Platform",
    }

    try:
        import httpx
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            body = resp.json()
            content_str = body["choices"][0]["message"]["content"]
            return _parse_json_content(content_str)
    except ImportError:
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            content_str = body["choices"][0]["message"]["content"]
            return _parse_json_content(content_str)
