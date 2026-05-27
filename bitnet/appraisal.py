"""Appraisal engine — LLM-based file valuation from metadata only."""

import json
import aiohttp
from datetime import datetime, timezone

RATE_TABLE = {
    "infrastructure": 185,
    "smart_contract": 250,
    "trading_system": 225,
    "ml_pipeline": 200,
    "api_service": 175,
    "frontend": 150,
    "documentation": 95,
    "configuration": 110,
    "test": 130,
    "script": 120,
    "data": 80,
    "blockchain": 240,
    "security": 220,
    "devops": 160,
    "accounting": 140,
    "financial": 160,
    "invoice": 130,
    "unknown": 100,
}

OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3"


async def ollama_available() -> bool:
    """Check if Ollama inference backend is available."""
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{OLLAMA_URL}/api/tags", timeout=aiohttp.ClientTimeout(total=5)) as r:
                return r.status == 200
    except Exception:
        return False


def heuristic_appraisal(filename: str, extension: str, file_size: int) -> dict:
    """Heuristic appraisal when no LLM is available."""
    ext = (extension or "").lower().lstrip(".")
    ext_cat = {
        "py": "infrastructure", "rs": "infrastructure", "go": "infrastructure",
        "js": "infrastructure", "ts": "infrastructure", "sol": "smart_contract",
        "json": "configuration", "yaml": "configuration", "yml": "configuration",
        "toml": "configuration", "csv": "data", "tsv": "data",
        "pdf": "documentation", "md": "documentation", "txt": "documentation",
        "html": "frontend", "css": "frontend", "tsx": "frontend",
    }
    name_lower = filename.lower()
    if any(k in name_lower for k in ("invoice", "inv-", "receipt")):
        cat = "invoice"
    elif any(k in name_lower for k in ("ledger", "revenue", "expense", "balance")):
        cat = "accounting"
    else:
        cat = ext_cat.get(ext, "data")

    kb = file_size / 1024
    complexity = min(1.0, max(0.1, 0.3 + (kb / 500) * 0.5))
    hours = max(0.5, min(40.0, 1.0 + kb / 100))
    rate = RATE_TABLE.get(cat, 100)
    value = round(rate * hours * complexity, 2)

    return {
        "category": cat,
        "complexity_score": round(complexity, 3),
        "estimated_hours": round(hours, 2),
        "reasoning": f"Heuristic: {filename} ({ext}, {file_size}B) classified as {cat}.",
        "hourly_rate": rate,
        "appraised_value_usd": value,
        "model_used": "heuristic",
    }


async def appraise_metadata(
    filename: str,
    extension: str,
    file_size: int,
) -> dict:
    """Appraise a file from metadata only (no content access)."""
    if not OLLAMA_URL:
        return heuristic_appraisal(filename, extension, file_size)

    prompt = (
        f"Metadata:\n"
        f"- filename: {filename}\n"
        f"- extension: {extension}\n"
        f"- size_bytes: {file_size}\n\n"
        "Based ONLY on the metadata above (not file contents), estimate the professional effort "
        "to CREATE a document like this. Output ONLY valid JSON:\n"
        '{"category":"<one of: financial, invoice, accounting, data, infrastructure, documentation>",'
        '"complexity_score":<float 0-1>,"estimated_hours":<float>,'
        '"reasoning":"<1-2 sentences about document type and estimated creation effort>"}'
    )
    system_msg = (
        "You are a metadata analyst that estimates document creation effort from filenames and metadata. "
        "You never see file contents. You assess the LABOR HOURS to create a document of this type and complexity. "
        "Always respond with valid JSON only."
    )

    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "system": system_msg,
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": 400},
                },
                timeout=aiohttp.ClientTimeout(total=120),
            ) as r:
                raw = (await r.json()).get("response", "{}")
                return _parse(raw, OLLAMA_MODEL, filename, extension, file_size)
    except Exception:
        return heuristic_appraisal(filename, extension, file_size)


def _parse(raw: str, model: str, filename: str, extension: str, file_size: int) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
    try:
        d = json.loads(raw)
        cat = str(d.get("category", "unknown")).lower().replace(" ", "_")
        complexity = min(1.0, max(0.0, float(d.get("complexity_score", 0.5))))
        hours = max(0.1, float(d.get("estimated_hours", 1)))
        rate = RATE_TABLE.get(cat, 100)
        value = round(rate * hours * complexity, 2)
        return {
            "category": cat,
            "complexity_score": complexity,
            "estimated_hours": hours,
            "reasoning": str(d.get("reasoning", "")),
            "hourly_rate": rate,
            "appraised_value_usd": value,
            "model_used": model,
        }
    except Exception:
        return heuristic_appraisal(filename, extension, file_size)
